#!/usr/bin/env python3
"""KISS checker — complexity metrics + Ollama over-engineering detection."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.ollama_utils import analyze_files_parallel, check_ollama_available

_MODEL = "devstral"
_PROMPT = "kiss_overengineering"
_CALC_COMPLEXITY = Path.home() / ".claude/scripts/cli/agents/code_analyzer/calculate_complexity.py"


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    model: str = _MODEL,
) -> dict:
    start = time.time()
    violations = []
    files_analyzed = 0

    # Part 1: cyclomatic complexity via existing script (always runs on full path)
    if _CALC_COMPLEXITY.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(_CALC_COMPLEXITY), "--path", str(path), "--format", "json"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                raw = json.loads(result.stdout)
                files_analyzed = raw.get("files_analyzed", 0)
                for issue in raw.get("complexity_issues", []):
                    issue_file = issue.get("file", "")
                    # In incremental mode, filter to changed files only
                    if files is not None:
                        changed_names = {f.name for f in files}
                        if Path(issue_file).name not in changed_names:
                            continue
                    violations.append({
                        "principle": "KISS",
                        "file": issue_file,
                        "line": 0,
                        "severity": issue.get("severity", "medium"),
                        "message": (
                            f"High complexity: {issue.get('function', '?')} — "
                            f"cyclomatic={issue.get('cyclomatic_complexity', '?')}, "
                            f"nesting={issue.get('nesting_depth', '?')}, "
                            f"lines={issue.get('lines', '?')}"
                        ),
                        "suggestion": "Simplify control flow; extract helper functions to reduce complexity",
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass

    # Part 2: Ollama over-engineering scan (only if available)
    if check_ollama_available(model):
        if files is not None:
            source_files = [f for f in files if f.suffix in {e for exts in _LANG_EXTENSIONS.values() for e in exts}]
        else:
            exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
            source_files = discover_files(path, exts)
            source_files = [f for f in source_files
                            if not any(m in f.name.lower() for m in _TEST_MARKERS)]
        if not files_analyzed:
            files_analyzed = len(source_files)

        for item in analyze_files_parallel(source_files, language, model, _PROMPT, agents=agents, no_cache=no_cache):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            violations.append({
                "principle": "KISS",
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "medium"),
                "message": f"Over-engineering [{item.get('pattern', '?')}]: {item.get('violation', '')}",
                "suggestion": item.get("suggestion", ""),
            })

    return {
        "principle": "KISS",
        "success": True,
        "violations": violations,
        "files_analyzed": files_analyzed,
        "duration_ms": int((time.time() - start) * 1000),
    }
