#!/usr/bin/env python3
"""Thin shim over the shared engine hybrid driver — injects SSA's prompts dir."""

from pathlib import Path

from lib.engine.hybrid import resolve_language, scan_patterns, select_files  # noqa: F401
from lib.engine.hybrid import run_hybrid as _run_hybrid

_AGENT_DIR = Path(__file__).parent.parent
_PROMPTS_DIR = _AGENT_DIR / "prompts" / "local"


def run_hybrid(*args, **kwargs) -> dict:
    from ssa import model_utils

    kwargs.setdefault("prompts_dir", _PROMPTS_DIR)
    kwargs.setdefault("model_cache", model_utils.CACHE)
    return _run_hybrid(*args, **kwargs)
