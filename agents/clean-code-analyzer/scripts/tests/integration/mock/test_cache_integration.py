"""Integration tests for cache module with real filesystem (no Ollama needed)."""

import os
import time
from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common.cache as cache_mod


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path):
    """Use tmp_path as cache directory for every test."""
    with patch.object(cache_mod, "_CACHE_DIR", tmp_path / ".cache"):
        yield tmp_path


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def process(data):\n    return data\n")
    return f


@pytest.mark.integration_mock
def test_cache_round_trip_integration(source_file):
    """set_cached + get_cached persists violations across calls."""
    violations = [
        {"principle": "Naming", "line": 5, "severity": "high", "message": "Bad name"},
    ]
    cache_mod.set_cached(source_file, "naming", violations)
    result = cache_mod.get_cached(source_file, "naming")
    assert result == violations


@pytest.mark.integration_mock
def test_cache_miss_on_file_change(source_file):
    """Modifying file content changes hash → cache miss."""
    violations = [{"line": 1}]
    cache_mod.set_cached(source_file, "naming", violations)

    source_file.write_text("def process(data):\n    return data * 2\n")  # changed

    result = cache_mod.get_cached(source_file, "naming")
    assert result is None


@pytest.mark.integration_mock
def test_cache_different_checkers_stored_separately(source_file):
    """Same file, different checkers → separate cache entries."""
    v1 = [{"principle": "Naming", "line": 1}]
    v2 = [{"principle": "ErrorHandling", "line": 5}]
    cache_mod.set_cached(source_file, "naming", v1)
    cache_mod.set_cached(source_file, "error_handling", v2)

    assert cache_mod.get_cached(source_file, "naming") == v1
    assert cache_mod.get_cached(source_file, "error_handling") == v2


@pytest.mark.integration_mock
def test_cache_ttl_expiry(source_file):
    """Entry older than TTL → expired and returns None."""
    cache_mod.set_cached(source_file, "naming", [{"line": 1}])
    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    old_mtime = time.time() - 10 * 86400  # 10 days old
    os.utime(cache_files[0], (old_mtime, old_mtime))

    result = cache_mod.get_cached(source_file, "naming", max_age_days=7)
    assert result is None


@pytest.mark.integration_mock
def test_no_cache_flag_bypasses(tmp_path, source_file):
    """When no_cache=True in analyze_file_with_model, cache not written or read."""
    _SHARED = Path.home() / ".claude" / "scripts"
    if str(_SHARED) not in sys.path:
        sys.path.insert(0, str(_SHARED))
    import model_utils as model_mod

    call_count = [0]
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test_prompt.prompt").write_text("{source}")

    def fake_call_model(prompt, role="fast", timeout=120):
        call_count[0] += 1
        return "[]"

    with patch.object(model_mod, "call_model", side_effect=fake_call_model), \
         patch.object(cache_mod, "_CACHE_DIR", tmp_path / ".nocache"):
        model_mod.analyze_file_with_model(
            source_file, "python", "fast", "test_prompt", prompts_dir=prompts_dir, no_cache=True
        )
        model_mod.analyze_file_with_model(
            source_file, "python", "fast", "test_prompt", prompts_dir=prompts_dir, no_cache=True
        )

    assert call_count[0] == 2  # Called both times — no caching
