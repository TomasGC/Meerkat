#!/usr/bin/env python3
"""Tests for parallel_analyzer.py — unit tests"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parallel_analyzer import AnalyzerRouter
from common.models import ProjectType

def test_select_analyzers_raises_when_no_match():
    router = AnalyzerRouter()
    for analyzer in router.analyzers:
        analyzer.can_analyze = lambda pi: False

    fake_info = MagicMock()
    fake_info.project_types = []

    with pytest.raises(ValueError, match="No analyzer found"):
        router.select_analyzers(fake_info)

def test_count_risks_by_level_empty():
    router = AnalyzerRouter()
    result = router._count_risks_by_level([])
    assert result == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

def test_count_risks_by_level_mixed():
    router = AnalyzerRouter()
    risks = [
        MagicMock(risk_level="CRITICAL"),
        MagicMock(risk_level="HIGH"),
        MagicMock(risk_level="HIGH"),
        MagicMock(risk_level="LOW"),
    ]
    result = router._count_risks_by_level(risks)
    assert result["CRITICAL"] == 1
    assert result["HIGH"] == 2
    assert result["LOW"] == 1
    assert result["MEDIUM"] == 0

def _make_mock_result(entry_count=2, scenario_count=5, tested=3, test_count=1):
    mock_matrix = MagicMock()
    mock_matrix.total_scenarios = scenario_count
    mock_matrix.tested_scenarios = tested
    mock_matrix.untested_scenarios = scenario_count - tested
    mock_matrix.coverage_percent = (tested / scenario_count * 100) if scenario_count else 0.0
    mock_result = MagicMock()
    mock_result.entry_points = [MagicMock()] * entry_count
    mock_result.test_cases = [MagicMock()] * test_count
    mock_result.scenarios = [MagicMock()] * scenario_count
    mock_result.coverage_matrix = mock_matrix
    mock_result.risk_assessment = []
    return mock_result

def test_generate_report_single_type_structure():
    router = AnalyzerRouter()
    project_info = MagicMock()
    project_info.to_dict.return_value = {"language": "python"}

    results = {ProjectType.REST_API: _make_mock_result(entry_count=2, scenario_count=5, tested=3)}
    report = router._generate_report(project_info, results, verbose=False)

    assert report["success"] is True
    assert report["summary"]["total_entry_points"] == 2
    assert report["summary"]["total_scenarios"] == 5
    assert report["summary"]["overall_coverage"] == 60.0

def test_generate_report_total_tests_in_summary():
    router = AnalyzerRouter()
    project_info = MagicMock()
    project_info.to_dict.return_value = {}

    results = {ProjectType.REST_API: _make_mock_result(test_count=7)}
    report = router._generate_report(project_info, results, verbose=False)

    assert report["summary"]["total_tests"] == 7

def test_analyzer_router_uses_thread_pool():
    import inspect
    import parallel_analyzer as pa
    source = inspect.getsource(pa.AnalyzerRouter.analyze_project)
    assert "ThreadPoolExecutor" in source
    assert "ProcessPoolExecutor" not in source

def test_count_risks_by_level_unknown_level():
    router = AnalyzerRouter()
    risks = [MagicMock(risk_level="UNKNOWN_LEVEL")]
    result = router._count_risks_by_level(risks)
    assert result.get("UNKNOWN_LEVEL", 0) == 1

def test_generate_report_hybrid_uses_hybrid_result():
    router = AnalyzerRouter()
    project_info = MagicMock()
    project_info.to_dict.return_value = {}

    api_result = _make_mock_result(entry_count=3, scenario_count=4, tested=2, test_count=1)
    hybrid_result = _make_mock_result(entry_count=5, scenario_count=8, tested=6, test_count=2)
    results = {
        ProjectType.REST_API: api_result,
        ProjectType.HYBRID: hybrid_result,
    }
    report = router._generate_report(project_info, results, verbose=False)
    assert report["summary"]["total_entry_points"] == 5
    assert report["summary"]["total_scenarios"] == 8
