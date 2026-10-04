"""Integration tests for cache module with real filesystem (no Ollama needed)."""

import os
import time
from pathlib import Path
from unittest.mock import patch
import sys

import pytest


_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import lib.engine.cache as cache_mod


@pytest.fixture
def cache_dir(tmp_path):
    """Cache directory for every test — engine's cache functions take this explicitly."""
    return tmp_path / ".cache"


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def process(data):\n    return data\n")
    return f


def test_cache_round_trip_integration(cache_dir, source_file):
    """set_cached + get_cached persists violations across calls."""
    violations = [
        {"principle": "Naming", "line": 5, "severity": "high", "message": "Bad name"},
    ]
    cache_mod.set_cached(cache_dir, source_file, "naming", violations)
    result = cache_mod.get_cached(cache_dir, source_file, "naming")
    assert result == violations


def test_cache_miss_on_file_change(cache_dir, source_file):
    """Modifying file content changes hash → cache miss."""
    violations = [{"line": 1}]
    cache_mod.set_cached(cache_dir, source_file, "naming", violations)

    source_file.write_text("def process(data):\n    return data * 2\n")  # changed

    result = cache_mod.get_cached(cache_dir, source_file, "naming")
    assert result is None


def test_cache_different_checkers_stored_separately(cache_dir, source_file):
    """Same file, different checkers → separate cache entries."""
    v1 = [{"principle": "Naming", "line": 1}]
    v2 = [{"principle": "ErrorHandling", "line": 5}]
    cache_mod.set_cached(cache_dir, source_file, "naming", v1)
    cache_mod.set_cached(cache_dir, source_file, "error_handling", v2)

    assert cache_mod.get_cached(cache_dir, source_file, "naming") == v1
    assert cache_mod.get_cached(cache_dir, source_file, "error_handling") == v2


def test_cache_ttl_expiry(cache_dir, source_file):
    """Entry older than TTL → expired and returns None."""
    cache_mod.set_cached(cache_dir, source_file, "naming", [{"line": 1}])
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    old_mtime = time.time() - 10 * 86400  # 10 days old
    os.utime(cache_files[0], (old_mtime, old_mtime))

    result = cache_mod.get_cached(cache_dir, source_file, "naming", max_age_days=7)
    assert result is None


def test_no_cache_flag_bypasses(cache_dir, tmp_path, source_file):
    """A CCA AI checker serves repeat runs from cache_dir; no_cache=True goes back to the model.

    Real checker, real run_hybrid, real on-disk cache — only the model call is faked.
    """
    from cca.checkers.check_solid import run as run_solid

    analyzed: list[list[Path]] = []

    def fake_analyze(files, *args, **kwargs):
        analyzed.append(list(files))
        return [{"source_file": str(f), "source_file_name": f.name, "principle": "SRP",
                 "line": 1, "severity": "medium", "violation": "does two things",
                 "suggestion": "split"} for f in files]

    with patch("cca.checkers.check_solid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", side_effect=fake_analyze):
        first = run_solid(tmp_path, "python", files=[source_file], cache_dir=cache_dir)
        second = run_solid(tmp_path, "python", files=[source_file], cache_dir=cache_dir)
        calls_after_cached_run = len(analyzed)
        bypass = run_solid(tmp_path, "python", files=[source_file], cache_dir=cache_dir, no_cache=True)

    assert calls_after_cached_run == 1          # second run: 0 AI calls
    assert (second["cache_hits"], second["cache_total"]) == (1, 1)
    assert second["violations"] == first["violations"]
    assert len(analyzed) == 2                   # no_cache run: model called again
    assert "cache_hits" not in bypass
