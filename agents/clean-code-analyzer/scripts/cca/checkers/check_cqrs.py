#!/usr/bin/env python3
"""CQRS checker — detects command/query separation violations via local AI."""

from pathlib import Path

from lib.engine.hybrid import run_hybrid
from cca.model_utils import check_server_available, PROMPTS_DIR

_PROMPT = "cqrs_analysis"


def _format(item: dict, rel: str) -> dict:
    return {
        "principle": "CQRS", "file": rel, "line": item.get("line", 0),
        "severity": item.get("severity", "medium"),
        "message": f"[{item.get('type', '?')}] {item.get('method', '?')}: {item.get('violation', '')}",
        "suggestion": item.get("suggestion", ""),
    }


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False, role: str = "analyzer",
        cache_dir: Path | None = None, cache_ttl_days: int = 7) -> dict:
    if not check_server_available(role):
        return {"principle": "CQRS", "success": False, "error": "Local AI model not available",
                "violations": [], "files_analyzed": 0, "duration_ms": 0}
    return run_hybrid(path, language, "CQRS", _PROMPT, {}, PROMPTS_DIR,
                       files=files, agents=agents, no_cache=no_cache, role=role,
                       cache_dir=cache_dir, cache_ttl_days=cache_ttl_days,
                       format_ai_violation=_format)
