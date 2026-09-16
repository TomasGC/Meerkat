#!/usr/bin/env python3
"""Tests for common/cache.py"""

import json
from pathlib import Path

import pytest

from common.cache import AnalysisCache
from common.models import (
    AnalysisResult,
    CoverageMatrix,
    Endpoint,
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    ProjectType,
    Scenario,
)

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

# ── get_cached_result / save_result ───────────────────────────────────────────

def _make_result(project_type: ProjectType = ProjectType.REST_API) -> AnalysisResult:
    return AnalysisResult(
        project_type=project_type,
        entry_points=[
            EntryPoint(
                type=EntryPointType.HTTP_ENDPOINT,
                name="/users",
                params=[],
                file_path="main.go",
                line_number=1,
            )
        ],
        test_cases=[],
        scenarios=[_make_scenario()],
        coverage_matrix=CoverageMatrix(
            total_scenarios=1,
            tested_scenarios=0,
            untested_scenarios=1,
            coverage_percent=0.0,
            gaps=[],
        ),
        risk_assessment=[],
    )

@pytest.fixture
def go_project(temp_dir):
    proj = temp_dir / "go-proj"
    proj.mkdir()
    (proj / "main.go").write_text("package main")
    (proj / "main_test.go").write_text("package main")
    return proj

def test_get_cached_result_no_file_returns_none(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_save_and_get_result_roundtrip(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    restored = cache.get_cached_result(go_project, "go", "APIAnalyzer")
    assert restored is not None
    assert restored.project_type is ProjectType.REST_API
    assert restored.entry_points[0].name == "/users"
    assert isinstance(restored.entry_points[0].type, EntryPointType)

def test_result_cache_is_per_analyzer(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    # A different analyzer must not be served the first one's entry
    assert cache.get_cached_result(go_project, "go", "CLIAnalyzer") is None

def test_result_cache_language_mismatch_returns_none(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    assert cache.get_cached_result(go_project, "python", "APIAnalyzer") is None

def test_result_cache_invalidated_by_source_change(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    (go_project / "main.go").write_text("package main // edited")
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_result_cache_invalidated_by_test_change(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    (go_project / "main_test.go").write_text("package main // edited")
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_result_cache_invalidated_by_new_source_file(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    (go_project / "handlers.go").write_text("package main")
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_result_cache_corrupt_payload_returns_none(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    cache._result_cache_path("APIAnalyzer").write_text("{not json")
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_result_cache_schema_drift_returns_none(temp_dir, go_project):
    """A payload whose result no longer matches the model must miss, not raise."""
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    path = cache._result_cache_path("APIAnalyzer")
    payload = json.loads(path.read_text())
    payload["result"]["project_type"] = "no_such_type"
    path.write_text(json.dumps(payload))
    assert cache.get_cached_result(go_project, "go", "APIAnalyzer") is None

def test_result_cache_path_sanitizes_analyzer_name(temp_dir):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    path = cache._result_cache_path("api/weird name")
    assert path.name == "result_api_weird_name.json"
    assert path.parent == cache.cache_dir

def test_save_result_records_cached_analyzers(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    cache.save_result(go_project, "go", "CLIAnalyzer", _make_result(ProjectType.CLI_APP))
    info = cache.get_cache_info()
    assert info["status"] == "active"
    assert info["cached_analyzers"] == ["APIAnalyzer", "CLIAnalyzer"]

# ── invalidate_all with results ───────────────────────────────────────────────

def test_invalidate_all_removes_result_files(temp_dir, go_project):
    cache = AnalysisCache(cache_dir=temp_dir / "cache")
    cache.save_result(go_project, "go", "APIAnalyzer", _make_result())
    result_path = cache._result_cache_path("APIAnalyzer")
    assert result_path.exists()
    cache.invalidate_all()
    assert not result_path.exists()

def test_invalidate_all_include_projects_clears_subdirs(temp_dir, go_project):
    base = temp_dir / "base-cache"
    scoped = AnalysisCache(cache_dir=base / "abc123def456")
    scoped.save_result(go_project, "go", "APIAnalyzer", _make_result())
    scoped_path = scoped._result_cache_path("APIAnalyzer")
    assert scoped_path.exists()

    # Base directory holds no files of its own; only recursion clears anything
    AnalysisCache(cache_dir=base).invalidate_all(include_projects=True)
    assert not scoped_path.exists()

def test_invalidate_all_without_include_projects_keeps_subdirs(temp_dir, go_project):
    base = temp_dir / "base-cache"
    scoped = AnalysisCache(cache_dir=base / "abc123def456")
    scoped.save_result(go_project, "go", "APIAnalyzer", _make_result())
    AnalysisCache(cache_dir=base).invalidate_all()
    assert scoped._result_cache_path("APIAnalyzer").exists()

def test_invalidate_all_skips_model_subdir(temp_dir):
    base = temp_dir / "base-cache"
    models = base / "models"
    models.mkdir(parents=True)
    (models / "abc_api.json").write_text("[]")
    AnalysisCache(cache_dir=base).invalidate_all(include_projects=True)
    # Model cache has its own clear function; invalidate_all must not touch it
    assert (models / "abc_api.json").exists()

# ── BBA_CACHE_DIR override ───────────────────────────────────────────────────

def test_cache_home_honours_env_override(temp_dir, monkeypatch):
    monkeypatch.setenv("BBA_CACHE_DIR", str(temp_dir / "redirected"))
    cache = AnalysisCache()
    assert cache.cache_dir == temp_dir / "redirected"

def test_model_cache_dir_honours_env_override(temp_dir, monkeypatch):
    from common.cache import _model_cache_dir

    monkeypatch.setenv("BBA_CACHE_DIR", str(temp_dir / "redirected"))
    assert _model_cache_dir() == temp_dir / "redirected" / "models"
