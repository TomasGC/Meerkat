#!/usr/bin/env python3
"""Crash bug checker — AST for Python, patterns plus AI for other languages."""

import ast
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.dedup import drop_near_duplicates, format_known_findings
from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR

_PRINCIPLE = "CrashBug"
_PROMPT = "crash_bugs"

_NON_PYTHON_EXTS = {
    ext for lang, exts in _LANG_EXTENSIONS.items()
    if lang != "python"
    for ext in exts
}

_PATTERNS = {
    "csharp": [
        (re.compile(r'\b(?:int|long|double|decimal|DateTime|Guid)\.Parse\s*\('),
         "Parse throws on malformed input — use TryParse", "medium",
         "Switch to TryParse and handle the failure branch"),
        (re.compile(r'\.(?:First|Single|Last)\s*\(\s*\)'),
         "First/Single/Last throws when the sequence is empty", "medium",
         "Use the OrDefault variant and check for null"),
        (re.compile(r'\bas\s+\w+\s*\)?\s*\.\w'),
         "Member access on the result of `as` — NullReferenceException when the cast fails", "high",
         "Check the result for null, or use a pattern match"),
    ],
    "go": [
        # No comma allowed left of the assignment, otherwise `v, ok := x.(T)` matches.
        (re.compile(r'^[^,]*:?=\s*[\w.]+\.\(\*?[\w.]+\)\s*$'),
         "Type assertion without comma-ok — panics on a type mismatch", "high",
         "Use `v, ok := x.(T)` and handle ok == false"),
    ],
    "typescript": [
        (re.compile(r'\bJSON\.parse\s*\('),
         "JSON.parse throws on malformed input", "medium",
         "Wrap in try/catch or validate the payload first"),
        (re.compile(r'\w+!\s*\.'),
         "Non-null assertion bypasses the null check — runtime TypeError risk", "low",
         "Narrow the type with an explicit check instead of `!`"),
    ],
    "javascript": [
        (re.compile(r'\bJSON\.parse\s*\('),
         "JSON.parse throws on malformed input", "medium",
         "Wrap in try/catch or validate the payload first"),
        (re.compile(r'\bparseInt\s*\(\s*[^,)]+\)'),
         "parseInt without a radix — parsing depends on the input prefix", "low",
         "Pass the radix explicitly, e.g. parseInt(value, 10)"),
    ],
    "powershell": [
        (re.compile(r'\[(?:int|long|decimal|datetime)\]\s*\$'),
         "Hard cast throws when the value does not convert", "medium",
         "Validate the value first or use a TryParse call"),
    ],
    "bash": [
        (re.compile(r'\brm\s+-rf?\s+"?\$'),
         "rm -rf on an unvalidated variable — deletes the wrong tree when empty", "high",
         "Guard with `[ -n \"$var\" ]` and quote the expansion"),
    ],
}


def _pattern_check(file: Path, root: Path, language: str) -> list[dict]:
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    patterns = _PATTERNS.get(language, [])
    if not patterns:
        return []

    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    violations = []
    for i, line in enumerate(content.splitlines(), 1):
        for pattern, message, severity, suggestion in patterns:
            if pattern.search(line):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": i,
                    "severity": severity,
                    "message": message,
                    "suggestion": suggestion,
                })
    return violations


def _check_python_file(file: Path, root: Path) -> list[dict]:
    violations = []
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file))
    except (OSError, SyntaxError):
        return []

    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)

    for node in ast.walk(tree):
        # Division without zero check: x / y where y is a name (not a literal)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Name):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": node.lineno,
                    "severity": "medium",
                    "message": f"Division by variable `{node.right.id}` without zero check — ZeroDivisionError risk",
                    "suggestion": f"Guard with `if {node.right.id} == 0` or use try/except ZeroDivisionError",
                })

        # Subscript on a name without prior length/key check
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if isinstance(node.slice, (ast.Constant, ast.Name)):
                parent_func = getattr(node, "_parent_func", None)
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": node.lineno,
                    "severity": "low",
                    "message": f"Subscript `{node.value.id}[...]` without bounds/key check — IndexError/KeyError risk",
                    "suggestion": f"Check `len({node.value.id})` or use `.get()` before subscripting",
                })

    return violations


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
) -> dict:
    start = time.time()
    violations = []

    if files is not None:
        source_files = [f for f in files if f.suffix in {e for exts in _LANG_EXTENSIONS.values() for e in exts}]
    else:
        exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
        source_files = discover_files(path, exts)
        source_files = [f for f in source_files if not any(m in f.name.lower() for m in _TEST_MARKERS)]

    python_files = [f for f in source_files if f.suffix == ".py"]
    non_python_files = [f for f in source_files if f.suffix in _NON_PYTHON_EXTS]

    for file in python_files:
        violations.extend(_check_python_file(file, path))

    per_file: dict[Path, list[dict]] = {}
    for file in non_python_files:
        lang = language if language != "mixed" else next(
            (l for l, exts in _LANG_EXTENSIONS.items() if file.suffix in exts), "unknown"
        )
        per_file[file] = _pattern_check(file, path, lang)
        violations.extend(per_file[file])

    if check_server_available(role) and non_python_files:
        extra_slots = {
            f: {"known_findings": format_known_findings(per_file.get(f, []))}
            for f in non_python_files
        }
        ai_violations = []
        for item in analyze_files_parallel(non_python_files, language, role, _PROMPT,
                                           prompts_dir=PROMPTS_DIR, agents=agents,
                                           no_cache=no_cache, extra_slots=extra_slots):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            ai_violations.append({
                "principle": _PRINCIPLE,
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "medium"),
                "message": f"[{item.get('bug_type', '?')}]: {item.get('description', '')}",
                "suggestion": item.get("fix", ""),
            })
        violations.extend(drop_near_duplicates(ai_violations, violations))

    return {
        "principle": _PRINCIPLE,
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
