#!/usr/bin/env python3
"""DRY checker — delegates to existing find_duplicates.py."""

import json
import subprocess
import sys
import time
from pathlib import Path

_FIND_DUPLICATES = Path.home() / ".claude/scripts/cli/agents/code_analyzer/find_duplicates.py"


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    start = time.time()

    if not _FIND_DUPLICATES.exists():
        return {
            "principle": "DRY",
            "success": False,
            "error": f"find_duplicates.py not found at {_FIND_DUPLICATES}",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": 0,
        }

    try:
        result = subprocess.run(
            [sys.executable, str(_FIND_DUPLICATES), "--path", str(path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {
            "principle": "DRY",
            "success": False,
            "error": "Timeout after 60s",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": 60000,
        }

    if result.returncode != 0 or not result.stdout.strip():
        return {
            "principle": "DRY",
            "success": False,
            "error": result.stderr[:300] or "No output",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": int((time.time() - start) * 1000),
        }

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "principle": "DRY",
            "success": False,
            "error": "Could not parse JSON output",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": int((time.time() - start) * 1000),
        }

    violations = []
    for dup in raw.get("duplicates", []):
        locs = dup.get("locations", [])
        primary = locs[0] if locs else {}
        others = locs[1:]
        file_str = primary.get("file", "unknown")
        lines_str = primary.get("lines", "0")
        line_start = int(lines_str.split("-")[0]) if "-" in lines_str else int(lines_str or 0)

        other_refs = ", ".join(f"{l['file']}:{l['lines']}" for l in others)
        violations.append({
            "principle": "DRY",
            "file": file_str,
            "line": line_start,
            "severity": dup.get("severity", "medium"),
            "message": f"Duplicate block ({dup.get('lines', '?')} lines, similarity {dup.get('similarity', '?')}) also at {other_refs}",
            "suggestion": "Extract duplicated logic into a shared function or module",
        })

    return {
        "principle": "DRY",
        "success": True,
        "violations": violations,
        "files_analyzed": raw.get("files_analyzed", 0),
        "duration_ms": int((time.time() - start) * 1000),
    }
