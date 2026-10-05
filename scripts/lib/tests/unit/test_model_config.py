"""Unit tests for scripts/model_config.py — singleton config reader."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import lib.config.model_config as mc
import pytest

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


def test_get_model_local_fast(tmp_path):
    """get_model('fast', 'local') returns local fast model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", "local")
    assert result == "qwen2.5-coder:7b"


def test_get_model_local_analyzer(tmp_path):
    """get_model('analyzer', 'local') returns local analyzer model."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("analyzer")
    assert result == "devstral-small-2"


def test_get_model_online_fast(tmp_path):
    """get_model('fast', 'online') returns online fast model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", "online")
    assert result == "claude-haiku-4-5-20251001"


def test_get_model_online_deep(tmp_path):
    """get_model('deep', 'online') returns online deep model name."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("deep", "online")
    assert result == "claude-opus-5"


# ── Singleton: _load() called only once ──────────────────────────────────────


def test_singleton_load_called_once(tmp_path):
    """Files are read on the first _load() only; later calls use the cached dict."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        mc.get_model("fast")
        with patch.object(Path, "read_text") as mock_read:
            mc.get_model("deep")
            mc.get_model("analyzer")
    assert mock_read.call_count == 0


# ── Auto-copy: template copied when local config missing ─────────────────────


def test_auto_copy_template_when_config_missing(tmp_path):
    """When local config is absent, template is copied and used."""
    _reset_singleton()
    template_file = tmp_path / "template_models_config.json"
    template_file.write_text(json.dumps(_SAMPLE_CONFIG))
    local_config = tmp_path / "local_models_config.json"

    with patch.object(mc, "_CONFIG_PATH", local_config), patch.object(mc, "_TEMPLATE_PATH", template_file):
        result = mc.get_model("fast")

    assert local_config.exists(), "local config should have been created from template"
    assert result == "qwen2.5-coder:7b"


def test_auto_copy_skipped_when_template_missing(tmp_path):
    """When both local config and template are absent, _load returns empty dict."""
    _reset_singleton()
    local_config = tmp_path / "local_models_config.json"
    template_file = tmp_path / "template_models_config.json"

    with patch.object(mc, "_CONFIG_PATH", local_config), patch.object(mc, "_TEMPLATE_PATH", template_file):
        result = mc._load()

    assert result == {}


# ── Missing role / provider: fallback and KeyError ───────────────────────────


def test_missing_role_returns_fallback(tmp_path):
    """get_model with unknown role returns fallback when provided."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("unknown_role", fallback="some-default")
    assert result == "some-default"


def test_missing_role_raises_without_fallback(tmp_path):
    """get_model with unknown role and no fallback raises KeyError."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        with pytest.raises(KeyError, match="unknown_role"):
            mc.get_model("unknown_role")


def test_missing_provider_returns_fallback(tmp_path):
    """get_model with unknown provider returns fallback when provided."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        result = mc.get_model("fast", provider="nonexistent", fallback="fallback-model")
    assert result == "fallback-model"


def test_missing_provider_raises_without_fallback(tmp_path):
    """get_model with unknown provider and no fallback raises KeyError."""
    _reset_singleton()
    config_file = tmp_path / "local_models_config.json"
    config_file.write_text(json.dumps(_SAMPLE_CONFIG))
    with patch.object(mc, "_CONFIG_PATH", config_file):
        with pytest.raises(KeyError):
            mc.get_model("fast", provider="nonexistent")


# ── Template merge: template is the base, local overrides it ────────────────


def _write_pair(tmp_path, template: dict, local) -> tuple[Path, Path]:
    template_file = tmp_path / "template_models_config.json"
    template_file.write_text(json.dumps(template))
    local_file = tmp_path / "local_models_config.json"
    local_file.write_text(local if isinstance(local, str) else json.dumps(local))
    return template_file, local_file


def test_template_field_added_later_reaches_older_local_file(tmp_path):
    """A role added to the template after the local file was written is still visible."""
    _reset_singleton()
    template = {"local": {"analyzer": "model-a", "guard": "guard-model"}}
    older_local = {"local": {"analyzer": "model-a"}}
    template_file, local_file = _write_pair(tmp_path, template, older_local)
    with patch.object(mc, "_CONFIG_PATH", local_file), patch.object(mc, "_TEMPLATE_PATH", template_file):
        assert mc.get_model("guard") == "guard-model"


def test_local_value_wins_over_template(tmp_path):
    """A role set in the local file overrides the template's value."""
    _reset_singleton()
    template = {"local": {"analyzer": "template-model", "fast": "template-fast"}}
    local = {"local": {"analyzer": "my-model"}}
    template_file, local_file = _write_pair(tmp_path, template, local)
    with patch.object(mc, "_CONFIG_PATH", local_file), patch.object(mc, "_TEMPLATE_PATH", template_file):
        assert mc.get_model("analyzer") == "my-model"
        assert mc.get_model("fast") == "template-fast"


def test_local_list_and_scalar_override_template(tmp_path):
    """Override wins on scalars and lists; dicts merge recursively."""
    _reset_singleton()
    template = {"local": {"provider": "ollama", "tags": ["a", "b"]}, "online": {"provider": "anthropic"}}
    local = {"local": {"tags": ["c"]}}
    template_file, local_file = _write_pair(tmp_path, template, local)
    with patch.object(mc, "_CONFIG_PATH", local_file), patch.object(mc, "_TEMPLATE_PATH", template_file):
        config = mc._load()
    assert config["local"] == {"provider": "ollama", "tags": ["c"]}
    assert config["online"] == {"provider": "anthropic"}


# ── Malformed JSON: degrades to the template, not to nothing ────────────────


def test_malformed_local_json_degrades_to_template(tmp_path):
    """A broken local_models_config.json falls back to the template's values."""
    _reset_singleton()
    template_file, local_file = _write_pair(tmp_path, _SAMPLE_CONFIG, "not valid json {{{")
    with patch.object(mc, "_CONFIG_PATH", local_file), patch.object(mc, "_TEMPLATE_PATH", template_file):
        assert mc._load() == _SAMPLE_CONFIG
