#!/usr/bin/env python3
"""File discovery, language detection, and git incremental utilities."""

import subprocess
import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.config import language_config

_DISCOVERY_CACHE: dict[tuple, list[Path]] = {}

_SKIP_DIRS = language_config.skip_dirs()
_LANG_EXTENSIONS: dict[str, list[str]] = language_config.language_extensions()
_ALL_EXTENSIONS = set(language_config.extensions())

_TEST_MARKERS = ("test", "spec", "fixture", "mock", "migration")


def discover_files(path: Path, extensions: list[str] | None = None) -> list[Path]:
    """Return source files under path, skipping irrelevant directories. Results cached."""
    cache_key = (path, tuple(sorted(extensions)) if extensions else None)
    if cache_key in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[cache_key]

    target_exts = set(extensions) if extensions else _ALL_EXTENSIONS
    results: list[Path] = []

    if path.is_file():
        results = [path] if path.suffix in target_exts else []
        _DISCOVERY_CACHE[cache_key] = results
        return results

    include_dockerfiles = extensions is None
    for item in path.rglob("*"):
        if item.is_file():
            match = item.suffix in target_exts or (
                include_dockerfiles and language_config.matches_filename("dockerfile", item.name)
            )
            if match and not any(part in _SKIP_DIRS for part in item.parts):
                results.append(item)

    results = sorted(results)
    _DISCOVERY_CACHE[cache_key] = results
    return results


def detect_language(path: Path) -> str:
    """Detect dominant language by counting source file extensions."""
    files = discover_files(path)
    counts: dict[str, int] = {lang: 0 for lang in _LANG_EXTENSIONS}

    for f in files:
        for lang, exts in _LANG_EXTENSIONS.items():
            if f.suffix in exts:
                counts[lang] += 1

    if not any(counts.values()):
        return "unknown"

    dominant = max(counts, key=lambda k: counts[k])
    total = sum(counts.values())
    if counts[dominant] / total < 0.6:
        return "mixed"
    return dominant


def get_changed_files(path: Path, since: str = "HEAD") -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True, text=True, cwd=str(path), timeout=10,
        )
        if result.returncode != 0:
            return None
        changed = [path / f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in changed if f.exists()]
    except Exception:
        return None


def get_branch_files(path: Path, base: str = "main") -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, cwd=str(path), timeout=10,
        )
        if result.returncode != 0:
            return None
        changed = [path / f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in changed if f.exists()]
    except Exception:
        return None


def get_staged_files(path: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(path), timeout=10,
        )
        if result.returncode != 0:
            return None
        staged = [path / f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in staged if f.exists()]
    except Exception:
        return None


def read_file_safe(path: Path, max_chars: int = 8000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(content) > max_chars:
        return content[:max_chars] + "\n// ... (truncated)"
    return content
