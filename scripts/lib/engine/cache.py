#!/usr/bin/env python3
"""Per-file result cache — SHA-256 content hash keyed by (file, checker), with TTL.

Cache directory is injected by the caller; this module carries no agent name.
"""

import hashlib
import json
import time
from pathlib import Path


def _file_hash(file_path: Path) -> str:
    try:
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except OSError:
        return "nohash"


def get_cached(cache_dir: Path, file_path: Path, checker: str, max_age_days: int = 7) -> list[dict] | None:
    """Return cached violations, or None if missing/expired (default TTL: 7 days)."""
    key = f"{_file_hash(file_path)}_{checker}"
    cache_file = cache_dir / f"{key}.json"
    if not cache_file.exists():
        return None
    if max_age_days > 0:
        age_seconds = time.time() - cache_file.stat().st_mtime
        if age_seconds > max_age_days * 86400:
            try:
                cache_file.unlink()
            except OSError:
                pass
            return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def set_cached(cache_dir: Path, file_path: Path, checker: str, violations: list[dict]) -> None:
    """Cache violations for file+checker."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = f"{_file_hash(file_path)}_{checker}"
    cache_file = cache_dir / f"{key}.json"
    try:
        cache_file.write_text(json.dumps(violations), encoding="utf-8")
    except OSError:
        pass


def clear_cache(cache_dir: Path) -> int:
    """Clear all cached results. Returns number of entries deleted."""
    if not cache_dir.exists():
        return 0
    count = 0
    for f in cache_dir.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count
