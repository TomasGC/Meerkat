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
