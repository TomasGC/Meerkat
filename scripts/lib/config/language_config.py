#!/usr/bin/env python3
"""Centralized language configuration — reads local_languages_config.json once at import time.

Auto-generates local_languages_config.json from template if it doesn't exist.
Mirrors model_config.py.
"""

import json
import re
import shutil
from pathlib import Path

_CLAUDE_DIR = Path.home() / ".claude"
_CONFIG_PATH = _CLAUDE_DIR / "configs" / "local_languages_config.json"
_TEMPLATE_PATH = _CLAUDE_DIR / "configs" / "template_languages_config.json"

# Singleton — loaded once at import time
_config: dict = {}


def _load() -> dict:
    global _config
    if _config:
        return _config
    if not _CONFIG_PATH.exists():
        if _TEMPLATE_PATH.exists():
            shutil.copy(_TEMPLATE_PATH, _CONFIG_PATH)
        else:
            return _config
    try:
        _config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return _config


def all_languages() -> dict[str, dict]:
    """Every configured language, name -> its definition."""
    return _load().get("languages", {})


def get_language(language: str) -> dict:
    """Definition for one language. Empty dict if unknown."""
    return all_languages().get(language, {})


def extensions(language: str | None = None) -> list[str]:
    """Extensions for one language, or every known extension when language is None."""
    if language is not None:
        return list(get_language(language).get("extensions", []))
    return sorted({e for lang in all_languages().values() for e in lang.get("extensions", [])})


def language_extensions() -> dict[str, list[str]]:
    """language -> [ext], the shape the agents' _LANG_EXTENSIONS used."""
    return {name: list(lang.get("extensions", [])) for name, lang in all_languages().items()}


def language_for_extension(ext: str) -> str | None:
    """Inverse lookup. First match wins, in config order."""
    ext = ext.lower()
    for name, lang in all_languages().items():
        if ext in lang.get("extensions", []):
            return name
    return None


def skip_dirs(language: str | None = None) -> set[str]:
    """Global skip set, plus that language's own additions."""
    dirs = set(_load().get("skip_dirs", []))
    if language is not None:
        dirs |= set(get_language(language).get("skip_dirs", []))
    return dirs


def extensions_where(field: str, value: bool = True) -> set[str]:
    """Extensions of every language whose boolean field equals value."""
    return {
        e
        for lang in all_languages().values()
        if bool(lang.get(field)) is value
        for e in lang.get("extensions", [])
    }


def comment_style_extensions(style: str) -> set[str]:
    """Extensions of every language using this comment style."""
    return {
        e
        for lang in all_languages().values()
        if lang.get("comment_style") == style
        for e in lang.get("extensions", [])
    }


def filename_patterns() -> dict[str, re.Pattern]:
    """language -> compiled filename pattern, for languages matched by name not extension."""
    return {
        name: re.compile(lang["filename_pattern"])
        for name, lang in all_languages().items()
        if lang.get("filename_pattern")
    }


def matches_filename(language: str, filename: str) -> bool:
    """True if filename matches that language's filename pattern."""
    pattern = get_language(language).get("filename_pattern")
    return bool(pattern) and bool(re.match(pattern, filename))


def standards_for(language: str, dialect: str | None = None) -> str | None:
    """Path to the rules/ document, dialect-specific when a dialect is given."""
    if dialect is not None:
        return _load().get("dialects", {}).get(language, {}).get(dialect, {}).get("standards")
    return get_language(language).get("standards")


def commands_for(language: str) -> dict[str, str | None]:
    """build / test / format commands for a language."""
    lang = get_language(language)
    return {key: lang.get(key) for key in ("build", "test", "format")}


def dialects(language: str) -> dict[str, dict]:
    """Configured dialects for a language. Empty when it has none."""
    return _load().get("dialects", {}).get(language, {})


def detect_dialect(language: str, content: str) -> str | None:
    """Dialect whose patterns hit most often in content.

    Ties break toward config order. Returns the dialect flagged `default` when
    nothing matches, else None — so an ambiguous file is never silently assigned.
    """
    candidates = dialects(language)
    if not candidates:
        return None

    best: str | None = None
    best_hits = 0
    default: str | None = None

    for name, spec in candidates.items():
        if spec.get("default"):
            default = name
        hits = sum(1 for p in spec.get("patterns", []) if re.search(p, content))
        if hits > best_hits:
            best, best_hits = name, hits

    return best or default


# Initialise at import time
_load()
