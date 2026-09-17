#!/usr/bin/env python3
"""Tests for common.cache module."""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.cache import SearchCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache(temp_cache_dir):
    """Create SearchCache instance with temp directory."""
    return SearchCache(cache_dir=temp_cache_dir, ttl_seconds=3600)


class TestSearchCache:
    """Test SearchCache functionality."""

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache directory creation."""
        cache_dir = temp_cache_dir / "new_cache"
        cache = SearchCache(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache.ttl_seconds == 3600

    def test_cache_key_generation(self, cache):
        """Test cache key generation is consistent."""
        key1 = cache._get_cache_key("test query", {"tag": "python"})
        key2 = cache._get_cache_key("test query", {"tag": "python"})
        key3 = cache._get_cache_key("other query", {"tag": "python"})

        assert key1 == key2  # Same query/filters = same key
        assert key1 != key3  # Different query = different key
        assert len(key1) == 16  # Hex hash truncated to 16 chars

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("nonexistent query", {})
        assert result is None

    def test_cache_hit(self, cache):
        """Test cache hit returns cached data."""
        query = "test query"
        filters = {"tag": "python"}
        data = {"results": [{"title": "Test"}]}

        # Cache data
        cache.set(query, filters, data)

        # Retrieve data
        cached = cache.get(query, filters)

        assert cached is not None
        assert cached == data

    def test_cache_expiration(self, temp_cache_dir):
        """Test cache expiration."""
        cache = SearchCache(cache_dir=temp_cache_dir, ttl_seconds=1)  # 1 second TTL

        query = "test query"
        filters = {}
        data = {"results": []}

        # Cache data
        cache.set(query, filters, data)

        # Immediate retrieval works
        cached = cache.get(query, filters)
        assert cached is not None

        # Wait for expiration
        time.sleep(1.1)

        # Expired data returns None
        cached = cache.get(query, filters)
        assert cached is None

    def test_cache_different_filters(self, cache):
        """Test different filters create different cache entries."""
        query = "test query"

        cache.set(query, {"tag": "python"}, {"data": "python"})
        cache.set(query, {"tag": "javascript"}, {"data": "javascript"})

        python_cached = cache.get(query, {"tag": "python"})
        js_cached = cache.get(query, {"tag": "javascript"})

        assert python_cached["data"] == "python"
        assert js_cached["data"] == "javascript"

    def test_cache_clear(self, cache):
        """Test clearing all cache."""
        cache.set("query1", {}, {"data": "1"})
        cache.set("query2", {}, {"data": "2"})

        # Verify cache has entries
        assert cache.get("query1", {}) is not None
        assert cache.get("query2", {}) is not None

        # Clear cache
        cache.clear()

        # Verify cache is empty
        assert cache.get("query1", {}) is None
        assert cache.get("query2", {}) is None

    def test_cache_clear_expired(self, temp_cache_dir):
        """Test clearing only expired entries."""
        cache = SearchCache(cache_dir=temp_cache_dir, ttl_seconds=3600)

        cache.set("fresh", {}, {"data": "fresh"})
        cache.set("stale", {}, {"data": "stale"})

        # Backdate one entry past the TTL instead of sleeping: the test then
        # proves clear_expired() is selective, which sleeping cannot show.
        stale_path = cache._get_cache_path(cache._get_cache_key("stale", {}))
        entry = json.loads(stale_path.read_text(encoding='utf-8'))
        entry['cached_at'] = (datetime.now() - timedelta(seconds=7200)).isoformat()
        stale_path.write_text(json.dumps(entry), encoding='utf-8')

        cache.clear_expired()

        assert cache.get("fresh", {}) == {"data": "fresh"}
        assert not stale_path.exists()

    def test_corrupted_cache_file(self, cache, temp_cache_dir):
        """Test handling of corrupted cache file."""
        query = "test"
        filters = {}

        # Create corrupted cache file
        cache_key = cache._get_cache_key(query, filters)
        cache_path = temp_cache_dir / f"{cache_key}.json"
        cache_path.write_text("invalid json {{{")

        # Should return None and delete corrupted file
        result = cache.get(query, filters)
        assert result is None
        assert not cache_path.exists()

    def test_default_cache_dir_is_under_home(self):
        """Default cache location must not be a world-writable shared directory."""
        from common.cache import _DEFAULT_CACHE_DIR

        assert _DEFAULT_CACHE_DIR.is_relative_to(Path.home())
        assert "tmp" not in _DEFAULT_CACHE_DIR.parts

    def test_cache_dir_created_owner_only(self, temp_cache_dir):
        """Cache directory must be created without group/other permissions."""
        cache_dir = temp_cache_dir / "perms"

        with patch.object(Path, "mkdir", autospec=True) as mkdir:
            SearchCache(cache_dir=cache_dir)

        _, kwargs = mkdir.call_args
        assert kwargs["mode"] & 0o077 == 0
        assert kwargs["mode"] == 0o700

    def test_set_swallows_write_failure(self, cache):
        """A failed cache write must not propagate to the caller."""
        with patch("common.cache.tempfile.mkstemp", side_effect=OSError("disk full")):
            cache.set("query", {}, {"data": "test"})  # must not raise

        assert cache.get("query", {}) is None

    def test_set_leaves_no_temp_files(self, cache, temp_cache_dir):
        """The atomic write must not leak its temp file."""
        cache.set("query", {}, {"data": "test"})

        assert list(temp_cache_dir.glob("*.tmp")) == []
        assert len(list(temp_cache_dir.glob("*.json"))) == 1

    def test_failed_write_leaves_no_temp_files(self, cache, temp_cache_dir):
        """A write that dies mid-flight must clean up after itself."""
        with patch("common.cache.json.dump", side_effect=OSError("io")):
            cache.set("query", {}, {"data": "test"})

        assert list(temp_cache_dir.glob("*.tmp")) == []

    def test_set_does_not_truncate_on_failure(self, cache):
        """A failed rewrite must leave the previous entry intact."""
        cache.set("query", {}, {"data": "original"})

        with patch("common.cache.os.replace", side_effect=OSError("io")):
            cache.set("query", {}, {"data": "replacement"})

        assert cache.get("query", {}) == {"data": "original"}

    def test_mismatched_query_is_rejected(self, cache):
        """An entry whose stored query differs from the request is not served."""
        cache.set("real query", {}, {"data": "secret"})

        cache_path = cache._get_cache_path(cache._get_cache_key("real query", {}))
        entry = json.loads(cache_path.read_text(encoding='utf-8'))
        entry['query'] = "attacker planted"
        cache_path.write_text(json.dumps(entry), encoding='utf-8')

        assert cache.get("real query", {}) is None
        assert not cache_path.exists()

    def test_mismatched_filters_are_rejected(self, cache):
        """An entry whose stored filters differ from the request is not served."""
        cache.set("q", {"tag": "python"}, {"data": "py"})

        cache_path = cache._get_cache_path(cache._get_cache_key("q", {"tag": "python"}))
        entry = json.loads(cache_path.read_text(encoding='utf-8'))
        entry['filters'] = {"tag": "javascript"}
        cache_path.write_text(json.dumps(entry), encoding='utf-8')

        assert cache.get("q", {"tag": "python"}) is None

    def test_entry_without_data_is_discarded(self, cache):
        """A structurally valid entry missing 'data' is treated as corrupt."""
        cache.set("q", {}, {"data": "x"})

        cache_path = cache._get_cache_path(cache._get_cache_key("q", {}))
        entry = json.loads(cache_path.read_text(encoding='utf-8'))
        del entry['data']
        cache_path.write_text(json.dumps(entry), encoding='utf-8')

        assert cache.get("q", {}) is None
        assert not cache_path.exists()

    def test_non_dict_entry_is_discarded(self, cache):
        """Valid JSON that is not an object must not crash get()."""
        cache_path = cache._get_cache_path(cache._get_cache_key("q", {}))
        cache_path.write_text('["not", "a", "dict"]', encoding='utf-8')

        assert cache.get("q", {}) is None
        assert not cache_path.exists()

    def test_unparseable_timestamp_is_expired(self, cache):
        """A garbage cached_at must expire the entry, not raise."""
        cache.set("q", {}, {"data": "x"})

        cache_path = cache._get_cache_path(cache._get_cache_key("q", {}))
        entry = json.loads(cache_path.read_text(encoding='utf-8'))
        entry['cached_at'] = "not-a-timestamp"
        cache_path.write_text(json.dumps(entry), encoding='utf-8')

        assert cache.get("q", {}) is None

    def test_concurrent_discard_is_tolerated(self, cache):
        """A file vanishing between read and unlink must not raise."""
        cache_path = cache._get_cache_path("deadbeefdeadbeef")

        cache._discard(cache_path)  # already absent
        assert not cache_path.exists()
