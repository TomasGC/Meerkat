#!/usr/bin/env python3
"""
Simple file-based cache for search results.

Reduces API calls by caching recent search results.
"""

import json
import hashlib
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Cache lives under the user's home, not a world-writable shared directory:
# /tmp entries are readable and tamperable by every local user.
_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "search-tech"


class SearchCache:
    """File-based cache for search results."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = 3600):
        """
        Initialize cache.

        Args:
            cache_dir: Cache directory (default: ~/.cache/search-tech)
            ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        if cache_dir is None:
            cache_dir = _DEFAULT_CACHE_DIR

        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

        # Owner-only: cached results may contain private query terms
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _get_cache_key(self, query: str, filters: Dict[str, Any]) -> str:
        """
        Generate cache key from query and filters.

        Args:
            query: Search query string
            filters: Query filters

        Returns:
            Cache key (hex hash)
        """
        cache_input = f"{query}:{json.dumps(filters, sort_keys=True)}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for key."""
        return self.cache_dir / f"{cache_key}.json"

    @staticmethod
    def _discard(cache_path: Path) -> None:
        """Delete a cache file, tolerating a concurrent deletion."""
        try:
            cache_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _load_entry(self, cache_path: Path) -> Optional[Dict[str, Any]]:
        """Read a cache entry, discarding it if unreadable or malformed."""
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError):
            self._discard(cache_path)
            return None

        if not isinstance(entry, dict):
            self._discard(cache_path)
            return None

        return entry

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """True when the entry is past its TTL or carries no usable timestamp."""
        try:
            cached_time = datetime.fromisoformat(entry['cached_at'])
        except (KeyError, TypeError, ValueError):
            return True

        return datetime.now() > cached_time + timedelta(seconds=self.ttl_seconds)

    def _write_atomic(self, cache_path: Path, entry: Dict[str, Any]) -> None:
        """Write the entry via a temp file + rename so readers never see a partial file."""
        fd, tmp_name = tempfile.mkstemp(dir=str(self.cache_dir), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            os.replace(tmp_name, cache_path)
        except (OSError, TypeError, ValueError):
            self._discard(Path(tmp_name))
            raise

    def get(self, query: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and not expired.

        Args:
            query: Search query string
            filters: Query filters

        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._get_cache_key(query, filters)
        cache_path = self._get_cache_path(cache_key)

        entry = self._load_entry(cache_path)
        if entry is None:
            return None

        if self._is_expired(entry):
            self._discard(cache_path)
            return None

        # The key is a truncated hash: confirm the entry really answers this
        # request before trusting it, so a colliding or tampered file is
        # dropped rather than served.
        if entry.get('query') != query or entry.get('filters') != filters:
            self._discard(cache_path)
            return None

        if 'data' not in entry:
            self._discard(cache_path)
            return None

        return entry['data']

    def set(self, query: str, filters: Dict[str, Any], data: Dict[str, Any]):
        """
        Cache search result.

        Args:
            query: Search query string
            filters: Query filters
            data: Data to cache
        """
        cache_key = self._get_cache_key(query, filters)
        cache_path = self._get_cache_path(cache_key)

        cached = {
            'cached_at': datetime.now().isoformat(),
            'query': query,
            'filters': filters,
            'data': data,
        }

        try:
            self._write_atomic(cache_path, cached)
        except (OSError, TypeError, ValueError):
            # A cache write failure must never break the caller's search
            pass

    def clear(self):
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.json"):
            self._discard(cache_file)

    def clear_expired(self):
        """Clear only expired cache files."""
        for cache_file in self.cache_dir.glob("*.json"):
            entry = self._load_entry(cache_file)
            if entry is None:
                continue  # _load_entry already discarded it

            if self._is_expired(entry):
                self._discard(cache_file)
