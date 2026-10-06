#!/usr/bin/env python3
"""Integration/mock test gap checker — mechanical "no test file in the tier" plus AI per-function gaps."""

from pathlib import Path

from bba.checkers._utils import run_gap_checker

_TIER = ["integration", "mock"]
_PROMPT = "integ_mock_gaps"
_PRINCIPLE = "INTEG_MOCK_GAP"


def _ai_message(item: dict) -> str:
    return (
        f"Missing mock integration test [{item.get('function', '?')}] "
        f"({item.get('interaction_type', '?')}): {item.get('reason', '')}"
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
        path,
        language,
        tier=_TIER,
        principle=_PRINCIPLE,
        prompt=_PROMPT,
        missing_message="No integration/mock test file found for this source file",
        ai_message=_ai_message,
        files=files,
        agents=agents,
        no_cache=no_cache,
        role=role,
        cache_dir=cache_dir,
        cache_ttl_days=cache_ttl_days,
    )
