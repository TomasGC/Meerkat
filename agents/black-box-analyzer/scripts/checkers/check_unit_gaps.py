#!/usr/bin/env python3
"""Unit test gap checker — hybrid (mechanical + model)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR
from checkers._utils import find_source_files, find_tier_test_files, has_test_in_tier

_TIER = ["unit"]
_PROMPT = "unit_gaps"
_PRINCIPLE = "UNIT_GAP"


def run(
    path: Path,
    language: str,
    files: list | None = None,
    role: str = "analyzer",
    no_cache: bool = False,
    **kwargs,
) -> dict:
    start = time.time()
    violations = []

    source_files = find_source_files(path, language, files)
    test_files = find_tier_test_files(path, _TIER)
    candidates = [f for f in source_files if not has_test_in_tier(f, test_files)]
    files_analyzed = len(source_files)

    if check_server_available(role) and candidates:
        for item in analyze_files_parallel(
            candidates, language, role, _PROMPT,
            prompts_dir=PROMPTS_DIR, no_cache=no_cache,
        ):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            violations.append({
                "principle": _PRINCIPLE,
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "medium"),
                "message": f"Missing unit test [{item.get('function', '?')}]: {item.get('reason', '')}",
                "suggestion": item.get("test_scenario", ""),
            })
    else:
        for f in candidates:
            rel = str(f.relative_to(path) if f.is_relative_to(path) else f)
            violations.append({
                "principle": _PRINCIPLE,
                "file": rel,
                "line": 0,
                "severity": "medium",
                "message": "No unit test file found for this source file",
                "suggestion": f"Add tests/unit/test_{f.stem}.py (or equivalent)",
            })

    return {
        "principle": _PRINCIPLE,
        "success": True,
        "violations": violations,
        "files_analyzed": files_analyzed,
        "duration_ms": int((time.time() - start) * 1000),
    }
