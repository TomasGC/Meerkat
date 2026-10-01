#!/usr/bin/env python3
"""DRY checker — delegates to existing find_duplicates.py."""

import json
import subprocess
import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
from lib.engine.hybrid import run_hybrid

_FIND_DUPLICATES = Path.home() / ".claude/scripts/cli/find_duplicates.py"


def _mechanical(path: Path, files: list | None) -> tuple[list[dict], int] | dict:
    if not _FIND_DUPLICATES.exists():
        return {"success": False, "error": f"find_duplicates.py not found at {_FIND_DUPLICATES}",
                "violations": [], "files_analyzed": 0}

    try:
        result = subprocess.run(
            [sys.executable, str(_FIND_DUPLICATES), "--path", str(path), "--format", "json"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout after 60s", "violations": [], "files_analyzed": 0}

    if result.returncode != 0 or not result.stdout.strip():
        return {"success": False, "error": result.stderr[:300] or "No output",
                "violations": [], "files_analyzed": 0}

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": "Could not parse JSON output",
                "violations": [], "files_analyzed": 0}

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
    return violations, raw.get("files_analyzed", 0)


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    return run_hybrid(path, language, "DRY", None, {}, files=files, mechanical_fn=_mechanical)
