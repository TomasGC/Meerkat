#!/usr/bin/env python3
"""Tests for common/cache.py"""

import json
from pathlib import Path

import pytest

from common.cache import AnalysisCache
from common.models import Endpoint, HTTPMethod, Parameter, Scenario, TestCase, TestFramework

# ── init ──────────────────────────────────────────────────────────────────────

def test_cache_init_creates_dir(temp_dir):
    cache_dir = temp_dir / "my-cache"
    assert not cache_dir.exists()
    cache = AnalysisCache(cache_dir=cache_dir)
    assert cache_dir.exists()

def test_cache_init_project_scoped(temp_dir):
    project = temp_dir / "my-project"
    project.mkdir()
    cache = AnalysisCache(project_path=project)
    # Two different projects should get different cache dirs
    project2 = temp_dir / "other-project"
    project2.mkdir()
    cache2 = AnalysisCache(project_path=project2)
    assert cache.cache_dir != cache2.cache_dir

def test_cache_init_same_project_same_dir(temp_dir):
    project = temp_dir / "proj"
    project.mkdir()
    c1 = AnalysisCache(project_path=project)
    c2 = AnalysisCache(project_path=project)
    assert c1.cache_dir == c2.cache_dir

# ── _hash_file ────────────────────────────────────────────────────────────────

def test_hash_file_deterministic(temp_dir):
    f = temp_dir / "file.py"
    f.write_text("hello world")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    h1 = cache._hash_file(f)
    h2 = cache._hash_file(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex

def test_hash_file_changes_on_content_change(temp_dir):
    f = temp_dir / "file.py"
    f.write_text("version 1")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    h1 = cache._hash_file(f)
    f.write_text("version 2")
    h2 = cache._hash_file(f)
    assert h1 != h2

def test_hash_file_missing_returns_empty(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    result = cache._hash_file(temp_dir / "nonexistent.py")
    assert result == ""

# ── _hash_directory ───────────────────────────────────────────────────────────

def test_hash_directory_finds_matching(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("x = 1")
    (proj / "helper.py").write_text("y = 2")
    (proj / "README.md").write_text("docs")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    hashes = cache._hash_directory(proj, ["*.py"])
    assert len(hashes) == 2
    assert all(k.endswith(".py") for k in hashes)

def test_hash_directory_empty(temp_dir):
    proj = temp_dir / "empty-proj"
    proj.mkdir()
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    hashes = cache._hash_directory(proj, ["*.py"])
    assert hashes == {}

# ── get_cached_endpoints — miss cases ────────────────────────────────────────

def test_get_cached_endpoints_no_cache_returns_none(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    result = cache.get_cached_endpoints(temp_dir, "python")
    assert result is None

def test_get_cached_endpoints_language_mismatch_returns_none(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    # Save as python, query as go
    cache.save_endpoints(proj, "python", [])
    result = cache.get_cached_endpoints(proj, "go")
    assert result is None

# ── save_endpoints / get_cached_endpoints round-trip ─────────────────────────

def _make_endpoint(path: str = "/users", method: HTTPMethod = HTTPMethod.GET) -> Endpoint:
    return Endpoint(
        path=path,
        method=method,
        params=[],
        response_codes=[200],
        file_path="main.py",
        line_number=1,
    )

def test_save_and_get_endpoints_roundtrip(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("# source")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    endpoints = [_make_endpoint("/users"), _make_endpoint("/orders", HTTPMethod.POST)]
    cache.save_endpoints(proj, "python", endpoints)
    result = cache.get_cached_endpoints(proj, "python")
    assert result is not None
    assert len(result) == 2
    paths = {ep.path for ep in result}
    assert "/users" in paths
    assert "/orders" in paths

def test_cache_miss_after_source_change(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    src = proj / "main.py"
    src.write_text("# v1")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_endpoints(proj, "python", [_make_endpoint()])
    src.write_text("# v2 changed")
    result = cache.get_cached_endpoints(proj, "python")
    assert result is None

# ── invalidate_all ────────────────────────────────────────────────────────────

def test_invalidate_all_clears_cache(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("x")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_endpoints(proj, "python", [_make_endpoint()])
    assert cache.endpoints_cache.exists()
    cache.invalidate_all()
    assert not cache.endpoints_cache.exists()
    assert not cache.metadata_cache.exists()

# ── get_cache_info ────────────────────────────────────────────────────────────

def test_get_cache_info_empty(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    info = cache.get_cache_info()
    assert info["status"] == "empty"

def test_get_cache_info_active(temp_dir):
    proj = temp_dir / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("x")
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_endpoints(proj, "python", [_make_endpoint()])
    info = cache.get_cache_info()
    assert info["status"] == "active"
    assert info["language"] == "python"

# ── get_cached_scenarios round-trip ──────────────────────────────────────────

def _make_scenario(endpoint: str = "/users") -> Scenario:
    return Scenario(
        endpoint=endpoint,
        method=HTTPMethod.GET,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
        description="test scenario",
    )

def test_save_and_get_scenarios_roundtrip(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    scenarios = [_make_scenario("/users"), _make_scenario("/orders")]
    cache.save_scenarios("abc123", scenarios)
    result = cache.get_cached_scenarios("abc123")
    assert result is not None
    assert len(result) == 2

def test_get_scenarios_hash_mismatch_returns_none(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_scenarios("hash-v1", [_make_scenario()])
    result = cache.get_cached_scenarios("hash-v2")
    assert result is None
