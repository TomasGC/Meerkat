#!/usr/bin/env python3
"""Thin shim over the shared engine hybrid driver — injects SSA's prompts dir."""

import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.engine.hybrid import resolve_language, scan_patterns, select_files  # noqa: F401
from lib.engine.hybrid import run_hybrid as _run_hybrid

_AGENT_DIR = Path(__file__).parent.parent
_PROMPTS_DIR = _AGENT_DIR / "prompts" / "local"


def run_hybrid(*args, **kwargs) -> dict:
    kwargs.setdefault("prompts_dir", _PROMPTS_DIR)
    return _run_hybrid(*args, **kwargs)
