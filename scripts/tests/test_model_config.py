"""Unit tests for scripts/model_config.py — singleton config reader."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import model_config as mc

_SAMPLE_CONFIG = {
    "local": {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "analyzer": "devstral-small-2",
        "fast": "qwen2.5-coder:7b",
        "deep": "qwen2.5-coder:14b",
        "reasoning": "qwen2.5:32b",
        "guard": "llama-guard3:8b",
    },
    "online": {
        "provider": "anthropic",
        "analyzer": "claude-sonnet-5",
        "fast": "claude-haiku-4-5-20251001",
        "deep": "claude-opus-5",
        "reasoning": "claude-opus-5",
    },
}


def _reset_singleton():
    """Clear the module-level _config singleton between tests."""
    mc._config = {}


# ── get_model: basic role resolution ─────────────────────────────────────────

@pytest.mark.unit
def test_get_model_local_fast(tmp_path):
    """get_model('fast', 'local') returns local fast model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", "local")
    assert result == "qwen2.5-coder:7b"


@pytest.mark.unit
def test_get_model_local_analyzer(tmp_path):
    """get_model('analyzer', 'local') returns local analyzer model."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("analyzer")
    assert result == "devstral-small-2"


@pytest.mark.unit
def test_get_model_online_fast(tmp_path):
    """get_model('fast', 'online') returns online fast model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", "online")
    assert result == "claude-haiku-4-5-20251001"


@pytest.mark.unit
def test_get_model_online_deep(tmp_path):
    """get_model('deep', 'online') returns online deep model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("deep", "online")
    assert result == "claude-opus-5"


# ── Singleton: _load() called only once ──────────────────────────────────────

@pytest.mark.unit
def test_singleton_load_called_once(tmp_path):
    """_load() reads the file only on first call; subsequent calls use cached dict."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        with patch.object(Path, "read_text", wraps=config_file.read_text) as mock_read:
            mc.get_model("fast")
            mc.get_model("deep")
            mc.get_model("analyzer")
    # read_text should be called at most once (first _load populates cache)
    assert mock_read.call_count <= 1


# ── Auto-copy: template copied when local config missing ─────────────────────

@pytest.mark.unit
def test_auto_copy_template_when_config_missing(tmp_path):
    """When local config is absent, template is copied and used."""
    _reset_singleton()
    template_file = tmp_path / "template_models_config.json"
    template_file.write_text(json.dumps(_SAMPLE_CONFIG))
    local_config = tmp_path / "local_models_config.json"

    with patch.object(mc, "_CONFIG_PATH", local_config), \
         patch.object(mc, "_TEMPLATE_PATH", template_file):
        result = mc.get_model("fast")

    assert local_config.exists(), "local config should have been created from template"
    assert result == "qwen2.5-coder:7b"


@pytest.mark.unit
def test_auto_copy_skipped_when_template_missing(tmp_path):
    """When both local config and template are absent, _load returns empty dict."""
    _reset_singleton()
    local_config = tmp_path / "local_models_config.json"
    template_file = tmp_path / "template_models_config.json"

    with patch.object(mc, "_CONFIG_PATH", local_config), \
         patch.object(mc, "_TEMPLATE_PATH", template_file):
        result = mc._load()

    assert result == {}


# ── Missing role / provider: fallback and KeyError ───────────────────────────

@pytest.mark.unit
def test_missing_role_returns_fallback(tmp_path):
    """get_model with unknown role returns fallback when provided."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("unknown_role", fallback="some-default")
    assert result == "some-default"


@pytest.mark.unit
def test_missing_role_raises_without_fallback(tmp_path):
    """get_model with unknown role and no fallback raises KeyError."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        with pytest.raises(KeyError, match="unknown_role"):
            mc.get_model("unknown_role")


@pytest.mark.unit
def test_missing_provider_returns_fallback(tmp_path):
    """get_model with unknown provider returns fallback when provided."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", provider="nonexistent", fallback="fallback-model")
    assert result == "fallback-model"


@pytest.mark.unit
def test_missing_provider_raises_without_fallback(tmp_path):
    """get_model with unknown provider and no fallback raises KeyError."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        with pytest.raises(KeyError):
            mc.get_model("fast", provider="nonexistent")


# ── Malformed JSON: _load handles gracefully ─────────────────────────────────

@pytest.mark.unit
def test_malformed_json_returns_empty_dict(tmp_path):
    """Malformed local_models_config.json causes _load to silently return {}."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text("not valid json {{{")
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc._load()
    assert result == {}
