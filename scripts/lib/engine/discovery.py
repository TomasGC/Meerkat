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

_HASH_COMMENT_EXTS = frozenset(language_config.comment_style_extensions("hash"))

# Python is excluded deliberately: check_inheritance handles it through a
# dedicated AST pass, and would scan every .py file twice otherwise.
_CLASS_LANG_EXTS = frozenset(
    language_config.extensions_where("has_inheritance") - set(language_config.extensions("python"))
)


def is_hash_comment_file(path: Path) -> bool:
    """True if file uses # for comments (Python, PS, Bash, YAML, Ruby, Perl, Dockerfile)."""
    return path.suffix in _HASH_COMMENT_EXTS or language_config.matches_filename("dockerfile", path.name)


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


def is_test_file(path: Path) -> bool:
    """True if the file name marks it as a test, spec, fixture, mock or migration."""
    name = path.name.lower()
    return any(m in name for m in _TEST_MARKERS)


def group_by_language(files: list[Path], kinds: tuple[str, ...] = ("code",)) -> dict[str, list[Path]]:
    """Split files by their own language, keeping only languages of the given kinds.

    Config order, so runs over the groups are deterministic.
    """
    wanted = language_config.languages_of_kind(*kinds)
    by_language: dict[str, list[Path]] = {}
    for f in files:
        language = language_config.language_for_file(f)
        if language in wanted:
            by_language.setdefault(language, []).append(f)
    return {name: by_language[name] for name in wanted if name in by_language}


def dominant_language(path: Path, threshold: float = 0.6) -> str:
    """Language most code files under path are written in — the one shared vote.

    Only `kind == "code"` languages vote: yaml, json or markdown must never
    outnumber the sources they sit beside. A repo with no code at all is voted
    on by its other files instead, so an SQL-only repo reads "sql". Returns
    "mixed" when the leader holds less than `threshold` of the votes
    (`threshold=0` always names the leader), "unknown" when no file has a
    language. Ties break toward config order.
    """
    files = discover_files(path)
    kinds = ("code",)
    counts = {name: len(group) for name, group in group_by_language(files, kinds).items()}
    if not counts:
        kinds = tuple({lang.get("kind") for lang in language_config.all_languages().values()} - {None})
        counts = {name: len(group) for name, group in group_by_language(files, kinds).items()}
    if not counts:
        return "unknown"
    leader = max(language_config.languages_of_kind(*kinds), key=lambda name: counts.get(name, 0))
    if counts[leader] / sum(counts.values()) < threshold:
        return "mixed"
    return leader


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
