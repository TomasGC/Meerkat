#!/usr/bin/env python3
"""Thin shim over the shared engine cache — SSA's cache directory."""

from pathlib import Path

from lib import paths
from lib.engine.cache import clear_cache as _clear_cache
from lib.engine.cache import get_cached as _get_cached
from lib.engine.cache import set_cached as _set_cached

_CACHE_DIR = paths.user_root() / "agents" / "security-safety-analyzer" / ".cache"


def get_cached(file_path: Path, checker: str, max_age_days: int = 7) -> list[dict] | None:
    return _get_cached(_CACHE_DIR, file_path, checker, max_age_days)


def set_cached(file_path: Path, checker: str, violations: list[dict]) -> None:
    _set_cached(_CACHE_DIR, file_path, checker, violations)


def clear_cache() -> int:
    return _clear_cache(_CACHE_DIR)
