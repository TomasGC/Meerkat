#!/usr/bin/env python3
"""Concurrency checker — pattern-based thread-safety scan plus AI race detection."""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.dedup import drop_near_duplicates, format_known_findings
from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR

_PRINCIPLE = "Concurrency"
_PROMPT = "concurrency"

_PATTERNS = {
    "csharp": [
        # Type part allows spaces so generics such as Dictionary<string, int> match.
        (re.compile(r'^\s*(?:private|public|internal|protected)?\s*static\s+'
                    r'(?!readonly\b|const\b|class\b|void\b)[\w.<>,\[\]?\s]+\s+\w+\s*='),
         "Mutable static field — shared across threads without synchronization", "high"),
        (re.compile(r'lock\s*\(\s*(?:this|typeof)\b'),
         "Locking on a publicly reachable object — external code can deadlock it", "medium"),
    ],
    "go": [
        (re.compile(r'\btime\.Sleep\s*\('),
         "Sleep used to order goroutines — race prone; synchronize explicitly", "medium"),
    ],
    "python": [
        (re.compile(r'\btime\.sleep\s*\('),
         "Sleep used to order threads — race prone; synchronize explicitly", "low"),
    ],
}

# Patterns that only matter when the file actually spawns concurrent work.
_CONCURRENCY_IMPORTS = {
    "python": re.compile(r'\b(?:import\s+threading|from\s+threading|concurrent\.futures|multiprocessing)\b'),
    "powershell": re.compile(r'\b(?:Start-Job|Start-ThreadJob|RunspacePool)\b'),
}

_SHARED_STATE = {
    "python": (re.compile(r'^\s*global\s+\w+'),
               "Global mutated from a threaded module — needs a lock", "high"),
    "powershell": (re.compile(r'\$global:\w+\s*='),
                   "Global variable written from a job — needs synchronization", "high"),
}

_GO_GOROUTINE = re.compile(r'\bgo\s+func\s*\(')
_GO_WAITGROUP_ADD = re.compile(r'\.Add\s*\(')


def _mechanical_check(file: Path, root: Path, language: str) -> list[dict]:
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    lines = content.splitlines()
    violations = []

    def add(line_no: int, message: str, severity: str) -> None:
        violations.append({
            "principle": _PRINCIPLE,
            "file": filename,
            "line": line_no,
            "severity": severity,
            "message": message,
            "suggestion": "Protect shared state with a lock or use an immutable/atomic alternative",
        })

    for i, line in enumerate(lines, 1):
        for pattern, message, severity in _PATTERNS.get(language, []):
            if pattern.search(line):
                add(i, message, severity)

    spawns_concurrency = language in _CONCURRENCY_IMPORTS and _CONCURRENCY_IMPORTS[language].search(content)
    if spawns_concurrency:
        pattern, message, severity = _SHARED_STATE[language]
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                add(i, message, severity)

    if language == "go":
        for i, line in enumerate(lines, 1):
            if not _GO_GOROUTINE.search(line):
                continue
            for offset, following in enumerate(lines[i:i + 3], 1):
                if _GO_WAITGROUP_ADD.search(following):
                    add(i + offset, "WaitGroup.Add called inside the goroutine — Wait can return early", "high")

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

    per_file: dict[Path, list[dict]] = {}
    for file in source_files:
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
                "message": f"[{item.get('issue_type', '?')}]: {item.get('description', '')}",
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
