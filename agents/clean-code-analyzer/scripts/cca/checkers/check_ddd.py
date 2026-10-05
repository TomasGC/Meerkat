#!/usr/bin/env python3
"""DDD checker — detects domain model violations via local AI."""

from pathlib import Path

from cca.model_utils import PROMPTS_DIR, check_server_available
from lib.engine.hybrid import run_hybrid

_PROMPT = "ddd_analysis"


def _format(item: dict, rel: str) -> dict:
    return {
        "principle": "DDD",
        "file": rel,
        "line": item.get("line", 0),
        "severity": item.get("severity", "medium"),
        "message": f"[{item.get('pattern', '?')}] {item.get('class_or_method', '?')}: {item.get('violation', '')}",
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
    if not check_server_available(role):
        return {
            "principle": "DDD",
            "success": False,
            "error": "Local AI model not available",
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": 0,
        }
    return run_hybrid(
        path,
        language,
        "DDD",
        _PROMPT,
        {},
        PROMPTS_DIR,
        files=files,
        agents=agents,
        no_cache=no_cache,
        role=role,
        cache_dir=cache_dir,
        cache_ttl_days=cache_ttl_days,
        format_ai_violation=_format,
    )
