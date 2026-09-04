"""Unit tests for common/cache.py — no external deps, isolated to tmp_path."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(SCRIPTS_DIR))

import common.cache as cache_mod


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path):
    """Redirect _CACHE_DIR to tmp_path for every test in this module."""
    with patch.object(cache_mod, "_CACHE_DIR", tmp_path / ".cache"):
        yield tmp_path


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("x = 1\n")
    return f


# ── get_cached ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_cached_returns_none_when_missing(source_file):
    """Cache miss returns None."""
    result = cache_mod.get_cached(source_file, "test_checker")
    assert result is None


@pytest.mark.unit
def test_set_get_cached_round_trip(source_file):
    """set_cached + get_cached returns the same list."""
    violations = [{"line": 5, "severity": "high", "message": "Bad code"}]
    cache_mod.set_cached(source_file, "test_checker", violations)
    result = cache_mod.get_cached(source_file, "test_checker")
    assert result == violations


@pytest.mark.unit
def test_get_cached_returns_none_when_expired(source_file):
    """Cache entry older than max_age_days is treated as expired → None."""
    violations = [{"line": 1, "severity": "low"}]
    cache_mod.set_cached(source_file, "test_checker", violations)

    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    # Set mtime to 8 days ago
    old_mtime = time.time() - 8 * 86400
    os.utime(cache_files[0], (old_mtime, old_mtime))

    result = cache_mod.get_cached(source_file, "test_checker", max_age_days=7)
    assert result is None


@pytest.mark.unit
def test_get_cached_returns_data_when_not_expired(source_file):
    """Cache entry 1 day old with 7-day TTL → returns data."""
    violations = [{"line": 1, "severity": "low"}]
    cache_mod.set_cached(source_file, "test_checker", violations)

    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    recent_mtime = time.time() - 1 * 86400
    os.utime(cache_files[0], (recent_mtime, recent_mtime))

    result = cache_mod.get_cached(source_file, "test_checker", max_age_days=7)
    assert result == violations


@pytest.mark.unit
def test_max_age_days_zero_never_expires(source_file):
    """max_age_days=0 disables TTL — returns data regardless of age."""
    violations = [{"line": 2, "severity": "medium"}]
    cache_mod.set_cached(source_file, "test_checker", violations)

    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    old_mtime = time.time() - 100 * 86400  # 100 days old
    os.utime(cache_files[0], (old_mtime, old_mtime))

    result = cache_mod.get_cached(source_file, "test_checker", max_age_days=0)
    assert result == violations


@pytest.mark.unit
def test_clear_cache_removes_json_files(source_file, tmp_path):
    """clear_cache() deletes all .json files and returns count."""
    cache_mod.set_cached(source_file, "checker_a", [{"line": 1}])
    cache_mod.set_cached(source_file, "checker_b", [{"line": 2}])

    cache_dir = cache_mod._CACHE_DIR
    assert len(list(cache_dir.glob("*.json"))) == 2

    count = cache_mod.clear_cache()
    assert count == 2
    assert len(list(cache_dir.glob("*.json"))) == 0


@pytest.mark.unit
def test_content_hash_changes_on_file_modification(tmp_path, source_file):
    """Changed file content → different hash key → cache miss."""
    violations = [{"line": 3, "severity": "high"}]
    cache_mod.set_cached(source_file, "test_checker", violations)

    # Modify file content → different SHA-256
    source_file.write_text("x = 99\n# completely different\n")

    result = cache_mod.get_cached(source_file, "test_checker")
    assert result is None


# ── error paths ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_file_hash_nonexistent_returns_nohash():
    """_file_hash on nonexistent file returns 'nohash' (OSError caught)."""
    result = cache_mod._file_hash(Path("/nonexistent_file_xyz_does_not_exist_at_all"))
    assert result == "nohash"


@pytest.mark.unit
def test_get_cached_corrupt_json_returns_none(source_file):
    """Cache file with invalid JSON → get_cached returns None."""
    cache_mod.set_cached(source_file, "test_checker", [{"line": 1}])
    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    cache_files[0].write_text("{ not valid json !!!}")
    result = cache_mod.get_cached(source_file, "test_checker")
    assert result is None


@pytest.mark.unit
def test_get_cached_unlink_oserror_returns_none(source_file):
    """OSError when unlinking expired file → returns None gracefully (no crash)."""
    import os
    violations = [{"line": 1}]
    cache_mod.set_cached(source_file, "test_checker", violations)
    cache_dir = cache_mod._CACHE_DIR
    cache_files = list(cache_dir.glob("*.json"))
    old_mtime = time.time() - 10 * 86400
    os.utime(cache_files[0], (old_mtime, old_mtime))
    with patch("pathlib.Path.unlink", side_effect=OSError("permission denied")):
        result = cache_mod.get_cached(source_file, "test_checker", max_age_days=7)
    assert result is None


@pytest.mark.unit
def test_set_cached_oserror_no_crash(source_file):
    """OSError when writing cache file → no exception raised, silently ignored."""
    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        cache_mod.set_cached(source_file, "test_checker", [{"line": 1}])
    # No exception = pass


@pytest.mark.unit
def test_clear_cache_dir_missing_returns_zero(tmp_path):
    """clear_cache when cache dir doesn't exist → returns 0 immediately."""
    with patch.object(cache_mod, "_CACHE_DIR", tmp_path / "nonexistent_cache_dir_xyz"):
        result = cache_mod.clear_cache()
    assert result == 0


@pytest.mark.unit
def test_clear_cache_unlink_oserror_skips_file(tmp_path):
    """OSError on unlink during clear_cache → file skipped, count reflects successes only."""
    cache_dir = tmp_path / ".cache_test_clear"
    cache_dir.mkdir()
    f1 = cache_dir / "entry1.json"
    f2 = cache_dir / "entry2.json"
    f1.write_text("{}")
    f2.write_text("{}")

    call_count = [0]
    original_unlink = Path.unlink

    def flaky_unlink(self, missing_ok=False):
        call_count[0] += 1
        if call_count[0] == 1:
            raise OSError("permission denied")
        original_unlink(self, missing_ok=missing_ok)

    with patch.object(cache_mod, "_CACHE_DIR", cache_dir):
        with patch.object(Path, "unlink", flaky_unlink):
            count = cache_mod.clear_cache()

    assert count == 1  # one succeeded, one failed
