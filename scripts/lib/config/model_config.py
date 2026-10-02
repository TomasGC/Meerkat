#!/usr/bin/env python3
"""Centralized model configuration — reads local_models_config.json once at import time.

Auto-generates local_models_config.json from template if it doesn't exist.
"""

import json
import shutil
from pathlib import Path

_CLAUDE_DIR = Path.home() / ".claude"
_CONFIG_PATH = _CLAUDE_DIR / "configs" / "local_models_config.json"
_TEMPLATE_PATH = _CLAUDE_DIR / "configs" / "template_models_config.json"

# Singleton — loaded once at import time
_config: dict = {}


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merge(base: dict, override: dict) -> dict:
    """Recursive merge; override wins on scalars and lists."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load() -> dict:
    global _config
    if _config:
        return _config
    if not _CONFIG_PATH.exists():
        if not _TEMPLATE_PATH.exists():
            return _config
        shutil.copy(_TEMPLATE_PATH, _CONFIG_PATH)
    # Template is the base, local overrides it — so a role added to the template
    # later still reaches a local file written before it, and a malformed local
    # file degrades to the template instead of to an empty config.
    _config = _merge(_read(_TEMPLATE_PATH), _read(_CONFIG_PATH))
    return _config


def get_model(role: str, provider: str = "local", fallback: str | None = None) -> str:
    """Return model name for role+provider. Falls back to fallback or raises if not found."""
    config = _load()
    model = config.get(provider, {}).get(role)
    if model:
        return model
    if fallback is not None:
        return fallback
    raise KeyError(f"Model role '{role}' not found for provider '{provider}' in {_CONFIG_PATH}")


# Initialise at import time
_load()
