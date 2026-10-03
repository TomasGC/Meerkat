#!/usr/bin/env python3
"""Real integration test gap checker — mechanical "no test file in the tier" plus AI per-function gaps."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # the agent scripts dir

from bba.checkers._utils import run_gap_checker

_TIER = ["integration", "real"]
_PROMPT = "integ_real_gaps"
_PRINCIPLE = "INTEG_REAL_GAP"


def _ai_message(item: dict) -> str:
    return (
        f"Missing real integration test [{item.get('function', '?')}] "
        f"({item.get('operation_type', '?')}): {item.get('reason', '')}"
    )


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
    cache_dir: Path | None = None,
    cache_ttl_days: int = 7,
    **kwargs,
) -> dict:
    return run_gap_checker(
        path, language, tier=_TIER, principle=_PRINCIPLE, prompt=_PROMPT,
        missing_message="No real integration test file found for this source file", ai_message=_ai_message,
        files=files, agents=agents, no_cache=no_cache, role=role,
        cache_dir=cache_dir, cache_ttl_days=cache_ttl_days,
    )
