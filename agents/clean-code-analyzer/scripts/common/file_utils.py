#!/usr/bin/env python3
"""File discovery, language detection, and git incremental utilities."""

import re
import subprocess
from pathlib import Path

_DOCKERFILE_PATTERN = re.compile(r'^[Dd]ockerfile(\.\w+)?$')

# Cache file discovery results — avoids repeated rglob across 12 checkers on same path
_DISCOVERY_CACHE: dict[tuple, list[Path]] = {}


_SKIP_DIRS = {
    ".git", "node_modules", "bin", "obj", "dist", "__pycache__",
    ".venv", "venv", "vendor", ".pytest_cache", "coverage", ".nyc_output",
    "build", "out", "target", ".tox", "eggs", ".eggs",
}

_LANG_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "csharp": [".cs"],
    "razor": [".cshtml", ".razor"],
    "go": [".go"],
    "powershell": [".ps1", ".psm1", ".psd1"],
    "bash": [".sh", ".bash"],
    "yaml": [".yaml", ".yml"],    # includes docker-compose, kubernetes, github actions
    "dockerfile": [],             # discovered by filename pattern, not extension
}

_ALL_EXTENSIONS = {ext for exts in _LANG_EXTENSIONS.values() for ext in exts}

_HASH_COMMENT_EXTS = frozenset(
    ext for lang in ("python", "powershell", "bash", "yaml") for ext in _LANG_EXTENSIONS.get(lang, [])
)

_CLASS_LANG_EXTS = frozenset(
    ext for lang, exts in _LANG_EXTENSIONS.items()
    if lang not in ("python", "bash", "yaml", "dockerfile") for ext in exts
)


def is_hash_comment_file(path: Path) -> bool:
    """True if file uses # for comments (Python, PS, Bash, YAML, Dockerfile)."""
    return path.suffix in _HASH_COMMENT_EXTS or bool(_DOCKERFILE_PATTERN.match(path.name))

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
                include_dockerfiles and bool(_DOCKERFILE_PATTERN.match(item.name))
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
    dominant_count = counts[dominant]

    # "mixed" if no single language > 60%
    if dominant_count / total < 0.6:
        return "mixed"

    return dominant


def get_changed_files(path: Path, since: str = "HEAD") -> list[Path] | None:
    """Return files changed since git ref. None if not a git repo or git unavailable."""
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
    """Files changed on current branch vs base branch (three-dot diff = since merge-base)."""
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
    """Return staged files (git diff --cached). None if not a git repo or git unavailable."""
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
    """Read file content, truncating at max_chars."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    if len(content) > max_chars:
        return content[:max_chars] + "\n// ... (truncated)"

    return content
