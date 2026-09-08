#!/usr/bin/env python3
"""CQRS checker — detects command/query separation violations via local AI."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import discover_files, _TEST_MARKERS
from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR

_PROMPT = "cqrs_analysis"


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False, role: str = "analyzer") -> dict:
    start = time.time()

    if not check_server_available(role):
        return {
            "principle": "CQRS",
            "success": False,
            "error": "Local AI model not available",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": 0,
        }

    if files is not None:
        source_files = list(files)
    else:
        source_files = discover_files(path)
        source_files = [f for f in source_files if not any(m in f.name.lower() for m in _TEST_MARKERS)]

    raw_items = analyze_files_parallel(source_files, language, role, _PROMPT, prompts_dir=PROMPTS_DIR, agents=agents, no_cache=no_cache)
    violations = []
    for item in raw_items:
        src = Path(item.get("source_file", ""))
        rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
        violations.append({
            "principle": "CQRS",
            "file": rel,
            "line": item.get("line", 0),
            "severity": item.get("severity", "medium"),
            "message": f"[{item.get('type', '?')}] {item.get('method', '?')}: {item.get('violation', '')}",
            "suggestion": item.get("suggestion", ""),
        })

    return {
        "principle": "CQRS",
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
