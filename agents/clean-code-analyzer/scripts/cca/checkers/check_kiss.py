#!/usr/bin/env python3
"""KISS checker — complexity metrics + local AI over-engineering detection."""

import json
import subprocess
import sys
from pathlib import Path

from cca.model_utils import PROMPTS_DIR
from lib import paths
from lib.engine.hybrid import run_hybrid

_PROMPT = "kiss_overengineering"
_CALC_COMPLEXITY = paths.SCRIPTS / "cli" / "calculate_complexity.py"


def _mechanical(path: Path, files: list | None) -> tuple[list[dict], int]:
    violations = []
    files_analyzed = 0
    if _CALC_COMPLEXITY.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(_CALC_COMPLEXITY), "--path", str(path), "--format", "json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            raw = json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None
            if raw is None or raw.get("success") is False:
                reason = (raw or {}).get("error") or result.stderr.strip()[:200] or f"exit code {result.returncode}"
                print(f"[WARN] KISS: {_CALC_COMPLEXITY.name} failed: {reason}", file=sys.stderr)
            else:
                files_analyzed = raw.get("files_analyzed", 0)
                for issue in raw.get("complexity_issues", []):
                    issue_file = issue.get("file", "")
                    if files is not None:
                        changed_names = {f.name for f in files}
                        if Path(issue_file).name not in changed_names:
                            continue
                    violations.append(
                        {
                            "principle": "KISS",
                            "file": issue_file,
                            "line": issue.get("line", 0),
                            "severity": issue.get("severity", "medium"),
                            "message": (
                                f"High complexity: {issue.get('function', '?')} — "
                                f"cyclomatic={issue.get('cyclomatic_complexity', '?')}, "
                                f"nesting={issue.get('nesting_depth', '?')}, "
                                f"lines={issue.get('lines', '?')}"
                            ),
                            "suggestion": "Simplify control flow; extract helper functions to reduce complexity",
                        }
                    )
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] KISS: {_CALC_COMPLEXITY.name} failed: {type(exc).__name__}", file=sys.stderr)
    return violations, files_analyzed


def _format(item: dict, rel: str) -> dict:
    return {
        "principle": "KISS",
        "file": rel,
        "line": item.get("line", 0),
        "severity": item.get("severity", "medium"),
        "message": f"Over-engineering [{item.get('pattern', '?')}]: {item.get('violation', '')}",
        "suggestion": item.get("suggestion", ""),
    }


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
    cache_dir: Path | None = None,
    cache_ttl_days: int = 7,
) -> dict:
    return run_hybrid(
        path,
        language,
        "KISS",
        _PROMPT,
        {},
        PROMPTS_DIR,
        files=files,
        agents=agents,
        no_cache=no_cache,
        role=role,
        cache_dir=cache_dir,
        cache_ttl_days=cache_ttl_days,
        mechanical_fn=_mechanical,
        format_ai_violation=_format,
    )
