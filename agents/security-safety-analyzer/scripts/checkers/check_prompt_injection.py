#!/usr/bin/env python3
"""Prompt injection checker — grep for unsanitized user data in LLM calls + AI deep scan."""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR
from common.dedup import drop_near_duplicates, format_known_findings

_PRINCIPLE = "PromptInjection"
_PROMPT = "prompt_injection"

# Mechanical: detect user-controlled data interpolated directly into prompt strings
_PYTHON_PATTERNS = [
    (re.compile(r'f["\'].*\{(?:user|input|request|query|message|content|data|text)[^}]*\}.*["\']'),
     "User-controlled variable interpolated directly into prompt f-string — prompt injection risk"),
    (re.compile(r'\.format\s*\(.*(?:user|input|request|query|message)'),
     "User-controlled variable passed to .format() on prompt string — prompt injection risk"),
    (re.compile(r'(?:system_prompt|user_prompt|prompt)\s*\+=\s*(?:user|input|request|query|message)'),
     "Prompt string concatenated with user input — prompt injection risk"),
]

_JS_TS_PATTERNS = [
    (re.compile(r'`[^`]*\$\{(?:user|input|request|query|message|content)[^}]*\}[^`]*`'),
     "User-controlled variable in template literal used as prompt — prompt injection risk"),
]


def _mechanical_check(file: Path, root: Path, language: str) -> list[dict]:
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    violations = []
    lines = content.splitlines()

    patterns = []
    if language == "python" or file.suffix == ".py":
        patterns = _PYTHON_PATTERNS
    elif language in ("javascript", "typescript") or file.suffix in (".js", ".ts", ".jsx", ".tsx"):
        patterns = _JS_TS_PATTERNS

    for i, line in enumerate(lines, 1):
        for pattern, message in patterns:
            if pattern.search(line):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": i,
                    "severity": "high",
                    "message": message,
                    "suggestion": "Sanitize or validate user input before including in prompts; use structured slots, not raw interpolation",
                })

    # Also scan .prompt files for unsanitized format slots
    if file.suffix == ".prompt":
        for i, line in enumerate(lines, 1):
            if re.search(r'\{(user_input|raw_input|message|query)\}', line):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": i,
                    "severity": "medium",
                    "message": "Prompt template contains a raw user-input slot — verify caller sanitizes before formatting",
                    "suggestion": "Document sanitization contract; consider using a wrapper that validates slot values",
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

    # Include .prompt files in addition to source files
    prompt_files = list(path.rglob("*.prompt")) if path.is_dir() else []

    if files is not None:
        source_files = [f for f in files if f.suffix in {e for exts in _LANG_EXTENSIONS.values() for e in exts}]
    else:
        exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
        source_files = discover_files(path, exts)
        source_files = [f for f in source_files if not any(m in f.name.lower() for m in _TEST_MARKERS)]

    all_files = source_files + [f for f in prompt_files if f not in source_files]

    per_file: dict[Path, list[dict]] = {}
    for file in all_files:
        lang = language if language != "mixed" else next(
            (l for l, exts in _LANG_EXTENSIONS.items() if file.suffix in exts), "unknown"
        )
        per_file[file] = _mechanical_check(file, path, lang)
        violations.extend(per_file[file])

    if check_server_available(role) and source_files:
        extra_slots = {
            f: {"known_findings": format_known_findings(per_file.get(f, []))}
            for f in source_files
        }
        ai_violations = []
        for item in analyze_files_parallel(source_files, language, role, _PROMPT,
                                           prompts_dir=PROMPTS_DIR, agents=agents,
                                           no_cache=no_cache, extra_slots=extra_slots):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            ai_violations.append({
                "principle": _PRINCIPLE,
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "high"),
                "message": f"[{item.get('injection_type', '?')}]: {item.get('description', '')}",
                "suggestion": item.get("fix", ""),
            })
        violations.extend(drop_near_duplicates(ai_violations, violations))

    return {
        "principle": _PRINCIPLE,
        "success": True,
        "violations": violations,
        "files_analyzed": len(all_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
