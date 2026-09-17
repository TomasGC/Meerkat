#!/usr/bin/env python3
"""Shared file discovery utilities for BBA checkers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common.constants import EXCLUDED_DIRS
from lib.config import language_config

_TEST_MARKERS = ("test", "spec", "fixture", "mock")

# Full table on purpose: gap checkers look for test files of any language.
_LANG_EXTENSIONS: dict[str, list[str]] = language_config.language_extensions()
_ALL_EXTENSIONS = set(language_config.extensions())


def is_test_file(f: Path) -> bool:
    name = f.stem.lower()
    return any(m in name for m in _TEST_MARKERS)


def find_source_files(path: Path, language: str, files: list | None = None) -> list[Path]:
    """Return non-test source files for analysis."""
    if files is not None:
        exts = set(_LANG_EXTENSIONS.get(language) or _ALL_EXTENSIONS)
        return [f for f in files if f.suffix in exts and not is_test_file(f)]
    exts = set(_LANG_EXTENSIONS.get(language) or _ALL_EXTENSIONS)
    return [
        f for f in path.rglob("*")
        if f.is_file()
        and f.suffix in exts
        and not any(p in EXCLUDED_DIRS for p in f.parts)
        and not is_test_file(f)
    ]


def find_tier_test_files(path: Path, tier_parts: list[str]) -> list[Path]:
    """Return files whose path contains tier_parts as consecutive segments."""
    n = len(tier_parts)
    result = []
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        parts = list(f.parts)
        if any(parts[i:i + n] == tier_parts for i in range(len(parts) - n + 1)):
            result.append(f)
    return result


def has_test_in_tier(src: Path, tier_test_files: list[Path]) -> bool:
    """True if any tier test file has a stem that contains the source stem."""
    base = src.stem.lower().removeprefix("test_").removesuffix("_test")
    return any(base in tf.stem.lower() for tf in tier_test_files)
