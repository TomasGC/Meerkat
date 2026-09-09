"""Unit tests for common/cache.py."""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import common.cache as cache_mod


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path):
    with patch.object(cache_mod, "_CACHE_DIR", tmp_path / ".ssa_cache"):
        yield tmp_path


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "service.py"
    f.write_text("x = 1\n")
    return f


class TestGetSetCached:
    def test_miss_returns_none(self, source_file):
        assert cache_mod.get_cached(source_file, "security") is None

    def test_round_trip(self, source_file):
        violations = [{"line": 5, "severity": "high", "message": "Bad"}]
        cache_mod.set_cached(source_file, "security", violations)
        assert cache_mod.get_cached(source_file, "security") == violations

    def test_expired_returns_none(self, source_file):
        cache_mod.set_cached(source_file, "security", [{"line": 1}])
        cache_dir = cache_mod._CACHE_DIR
        cache_files = list(cache_dir.glob("*.json"))
        old_mtime = time.time() - 8 * 86400
        os.utime(cache_files[0], (old_mtime, old_mtime))
        assert cache_mod.get_cached(source_file, "security", max_age_days=7) is None

    def test_not_expired_returns_data(self, source_file):
        violations = [{"line": 2}]
        cache_mod.set_cached(source_file, "security", violations)
        cache_dir = cache_mod._CACHE_DIR
        cache_files = list(cache_dir.glob("*.json"))
        recent_mtime = time.time() - 1 * 86400
        os.utime(cache_files[0], (recent_mtime, recent_mtime))
        assert cache_mod.get_cached(source_file, "security", max_age_days=7) == violations

    def test_content_hash_change_invalidates(self, source_file):
        cache_mod.set_cached(source_file, "security", [{"line": 1}])
        source_file.write_text("y = 99\n# different\n")
        assert cache_mod.get_cached(source_file, "security") is None

    def test_ttl_zero_never_expires(self, source_file):
        violations = [{"line": 3}]
        cache_mod.set_cached(source_file, "security", violations)
        cache_dir = cache_mod._CACHE_DIR
        cache_files = list(cache_dir.glob("*.json"))
        os.utime(cache_files[0], (time.time() - 100 * 86400, time.time() - 100 * 86400))
        assert cache_mod.get_cached(source_file, "security", max_age_days=0) == violations


class TestClearCache:
    def test_clears_all_entries(self, source_file):
        cache_mod.set_cached(source_file, "security", [{"line": 1}])
        cache_mod.set_cached(source_file, "crash_bugs", [{"line": 2}])
        count = cache_mod.clear_cache()
        assert count == 2
        assert list(cache_mod._CACHE_DIR.glob("*.json")) == []

    def test_missing_dir_returns_zero(self, tmp_path):
        with patch.object(cache_mod, "_CACHE_DIR", tmp_path / "no_such_dir"):
            assert cache_mod.clear_cache() == 0
