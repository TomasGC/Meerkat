"""Tests for the per-file result cache."""

import pytest

from lib.engine.cache import clear_cache, get_cached, set_cached


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / ".cache"


class TestGetCached:
    def test_miss_returns_none(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        assert get_cached(cache_dir, f, "solid_analysis") is None

    def test_round_trip(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        violations = [{"principle": "SOLID", "line": 10, "severity": "high"}]
        set_cached(cache_dir, f, "solid_analysis", violations)
        result = get_cached(cache_dir, f, "solid_analysis")
        assert result == violations

    def test_different_checkers_independent(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        v1 = [{"principle": "SOLID"}]
        v2 = [{"principle": "DDD"}]
        set_cached(cache_dir, f, "solid_analysis", v1)
        set_cached(cache_dir, f, "ddd_analysis", v2)
        assert get_cached(cache_dir, f, "solid_analysis") == v1
        assert get_cached(cache_dir, f, "ddd_analysis") == v2

    def test_content_change_invalidates_cache(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        violations = [{"principle": "SOLID"}]
        set_cached(cache_dir, f, "solid_analysis", violations)
        # Modify file — hash changes
        f.write_text("x = 2")
        assert get_cached(cache_dir, f, "solid_analysis") is None

    def test_corrupted_cache_returns_none(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        set_cached(cache_dir, f, "solid_analysis", [])
        # Corrupt the cache file
        from lib.engine.cache import _file_hash

        key = f"{_file_hash(f)}_solid_analysis"
        cache_file = cache_dir / f"{key}.json"
        cache_file.write_text("{invalid json")
        assert get_cached(cache_dir, f, "solid_analysis") is None


class TestCacheTTL:
    def test_expired_cache_returns_none(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        set_cached(cache_dir, f, "solid_analysis", [{"v": 1}])

        # Backdate mtime to 8 days ago
        from lib.engine.cache import _file_hash

        key = f"{_file_hash(f)}_solid_analysis"
        cache_file = cache_dir / f"{key}.json"
        old_mtime = cache_file.stat().st_mtime - (8 * 86400)
        import os

        os.utime(cache_file, (old_mtime, old_mtime))

        result = get_cached(cache_dir, f, "solid_analysis", max_age_days=7)
        assert result is None

    def test_fresh_cache_not_expired(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        set_cached(cache_dir, f, "solid_analysis", [{"v": 1}])
        # Default 7-day TTL — just written, so should still be fresh
        result = get_cached(cache_dir, f, "solid_analysis", max_age_days=7)
        assert result == [{"v": 1}]

    def test_ttl_zero_never_expires(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1")
        set_cached(cache_dir, f, "solid_analysis", [{"v": 99}])

        # Backdate mtime to 365 days ago
        from lib.engine.cache import _file_hash

        key = f"{_file_hash(f)}_solid_analysis"
        cache_file = cache_dir / f"{key}.json"
        old_mtime = cache_file.stat().st_mtime - (365 * 86400)
        import os

        os.utime(cache_file, (old_mtime, old_mtime))

        result = get_cached(cache_dir, f, "solid_analysis", max_age_days=0)
        assert result == [{"v": 99}]


class TestClearCache:
    def test_clear_empty(self, cache_dir):
        assert clear_cache(cache_dir) == 0

    def test_clear_removes_entries(self, cache_dir, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x")
        set_cached(cache_dir, f, "solid_analysis", [])
        set_cached(cache_dir, f, "ddd_analysis", [])
        assert clear_cache(cache_dir) == 2
        assert clear_cache(cache_dir) == 0
