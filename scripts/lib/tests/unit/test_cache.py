#!/usr/bin/env python3
"""Tests for lib/engine/cache.py — per-file result cache keyed by content hash and checker."""

import os
import time

from lib.engine.cache import clear_cache, get_cached, set_cached

FINDINGS = [{"principle": "DRY", "file": "a.py", "line": 3}]


def test_round_trip_per_checker(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"

    set_cached(cache_dir, source, "dry", FINDINGS)

    assert get_cached(cache_dir, source, "dry") == FINDINGS
    assert get_cached(cache_dir, source, "kiss") is None


def test_edit_to_the_file_misses_the_cache(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    set_cached(tmp_path / "cache", source, "dry", FINDINGS)

    source.write_text("x = 2\n", encoding="utf-8")

    assert get_cached(tmp_path / "cache", source, "dry") is None


def test_expired_entry_is_deleted(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    set_cached(cache_dir, source, "dry", FINDINGS)
    (entry,) = cache_dir.glob("*.json")
    old = time.time() - 3 * 86400
    os.utime(entry, (old, old))

    assert get_cached(cache_dir, source, "dry", max_age_days=2) is None
    assert not entry.exists()


def test_zero_ttl_never_expires(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    set_cached(cache_dir, source, "dry", FINDINGS)
    (entry,) = cache_dir.glob("*.json")
    os.utime(entry, (0, 0))

    assert get_cached(cache_dir, source, "dry", max_age_days=0) == FINDINGS


def test_corrupt_entry_reads_as_miss(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x\n", encoding="utf-8")
    cache_dir = tmp_path / "cache"
    set_cached(cache_dir, source, "dry", FINDINGS)
    (entry,) = cache_dir.glob("*.json")
    entry.write_text("{not json", encoding="utf-8")

    assert get_cached(cache_dir, source, "dry") is None


def test_unreadable_source_shares_the_nohash_key(tmp_path):
    missing = tmp_path / "gone.py"
    set_cached(tmp_path / "cache", missing, "dry", FINDINGS)
    assert [p.name for p in (tmp_path / "cache").glob("*.json")] == ["nohash_dry.json"]


def test_clear_cache_counts_deleted_entries(tmp_path):
    cache_dir = tmp_path / "cache"
    for name in ("a", "b"):
        source = tmp_path / f"{name}.py"
        source.write_text(name, encoding="utf-8")
        set_cached(cache_dir, source, "dry", [])
    (cache_dir / "keep.txt").write_text("not an entry", encoding="utf-8")

    assert clear_cache(cache_dir) == 2
    assert [p.name for p in cache_dir.iterdir()] == ["keep.txt"]


def test_clear_cache_without_directory(tmp_path):
    assert clear_cache(tmp_path / "absent") == 0
