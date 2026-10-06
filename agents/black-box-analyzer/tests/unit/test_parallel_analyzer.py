#!/usr/bin/env python3
"""Tests for parallel_analyzer.py — unit tests"""

from unittest.mock import MagicMock

import pytest

from bba.models import (
    AnalysisResult,
    CoverageGap,
    CoverageMatrix,
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    Language,
    ProjectInfo,
    ProjectType,
    RiskAssessment,
    Scenario,
    TestCase,
    TestFramework,
)
from parallel_analyzer import AnalyzerRouter


def test_select_analyzers_raises_when_no_match():
    router = AnalyzerRouter()
    for analyzer in router.analyzers:
        analyzer.can_analyze = lambda _project_info: False

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


# ── analyze_project: routing, cache, aggregation ──────────────────────────────


def _scenario(endpoint, method=HTTPMethod.GET):
    return Scenario(
        endpoint=endpoint,
        method=method,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )


def _result(project_type, endpoints, tested_endpoint=None, risk_level="HIGH"):
    scenarios = [_scenario(e) for e in endpoints]
    tests = []
    if tested_endpoint:
        tests.append(
            TestCase(
                name="t",
                file_path="t.py",
                line_number=1,
                framework=TestFramework.PYTEST,
                tested_endpoint=tested_endpoint,
            )
        )
    risks = [
        RiskAssessment(
            gap=CoverageGap(scenario=s, is_tested=False),
            business_impact=3,
            technical_risk=3,
            failure_probability=3,
            risk_score=27,
            risk_level=risk_level,
            reasoning="r",
        )
        for s in scenarios
    ]
    return AnalysisResult(
        project_type=project_type,
        entry_points=[
            EntryPoint(type=EntryPointType.HTTP_ENDPOINT, name=e, params=[], file_path="m.py", line_number=1)
            for e in endpoints
        ],
        test_cases=tests,
        scenarios=scenarios,
        coverage_matrix=CoverageMatrix(
            total_scenarios=len(scenarios),
            tested_scenarios=0,
            untested_scenarios=len(scenarios),
            coverage_percent=0.0,
            gaps=[],
        ),
        risk_assessment=risks,
    )


class _FakeAnalyzer:
    def __init__(self, result=None, error=None, accepts=True):
        self._result = result
        self._error = error
        self._accepts = accepts
        self.calls = 0

    def can_analyze(self, _project_info):
        return self._accepts

    def analyze(self, _project_path, _project_info):
        self.calls += 1
        if self._error:
            raise self._error
        return self._result


def _project_info(root, types=(ProjectType.REST_API,)):
    return ProjectInfo(
        language=Language.PYTHON,
        frameworks=["fastapi"],
        endpoint_count=1,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0],
    )


def _router_with(monkeypatch, root, analyzers, types=(ProjectType.REST_API,)):
    import parallel_analyzer as pa

    monkeypatch.setattr(pa, "detect_project_structure", lambda _path: _project_info(root, types))
    router = AnalyzerRouter()
    router.analyzers = analyzers
    return router


def test_select_analyzers_keeps_only_accepting_analyzers(tmp_path):
    router = AnalyzerRouter()
    yes = _FakeAnalyzer(accepts=True)
    router.analyzers = [_FakeAnalyzer(accepts=False), yes]
    assert router.select_analyzers(_project_info(tmp_path)) == [yes]


def test_analyze_project_single_type_report(monkeypatch, tmp_path):
    analyzer = _FakeAnalyzer(_result(ProjectType.REST_API, ["/a", "/b"]))
    router = _router_with(monkeypatch, tmp_path, [analyzer])

    report = router.analyze_project(tmp_path, use_cache=False)

    assert report["success"] is True
    assert list(report["results"]) == ["rest_api"]
    assert report["summary"]["total_entry_points"] == 2
    assert report["results"]["rest_api"]["risks"]["by_level"]["HIGH"] == 2
    assert report["cache"] == {"enabled": False, "hits": 0, "misses": 1}


def test_analyze_project_hybrid_aggregates_components(monkeypatch, tmp_path):
    api = _FakeAnalyzer(_result(ProjectType.REST_API, ["/a", "/b"], tested_endpoint="/a"))
    cli = _FakeAnalyzer(_result(ProjectType.CLI_APP, ["deploy"]))
    router = _router_with(monkeypatch, tmp_path, [api, cli], types=(ProjectType.REST_API, ProjectType.CLI_APP))

    report = router.analyze_project(tmp_path, use_cache=False)

    assert set(report["results"]) == {"rest_api", "cli_app", "hybrid"}
    hybrid = report["results"]["hybrid"]
    assert hybrid["entry_points"] == 3
    # One of three scenarios has a matching test across components
    assert hybrid["coverage"]["tested_scenarios"] == 1
    assert hybrid["coverage"]["coverage_percent"] == 33.33
    assert report["summary"]["total_entry_points"] == 3
    assert report["summary"]["total_risks"] == 3


def test_aggregate_results_records_component_types(tmp_path):
    router = AnalyzerRouter()
    results = {
        ProjectType.REST_API: _result(ProjectType.REST_API, ["/a"]),
        ProjectType.CLI_APP: _result(ProjectType.CLI_APP, []),
    }
    aggregated = router._aggregate_results(results, _project_info(tmp_path))
    assert aggregated.project_type is ProjectType.HYBRID
    assert aggregated.metadata["component_types"] == ["rest_api", "cli_app"]
    assert aggregated.coverage_matrix.coverage_percent == 0.0


def test_aggregate_results_method_mismatch_is_untested(tmp_path):
    router = AnalyzerRouter()
    result = _result(ProjectType.REST_API, ["/a"])
    result.test_cases = [
        TestCase(
            name="t",
            file_path="t.py",
            line_number=1,
            framework=TestFramework.PYTEST,
            tested_endpoint="/a",
            tested_method=HTTPMethod.POST,
        )
    ]
    aggregated = router._aggregate_results({ProjectType.REST_API: result}, _project_info(tmp_path))
    assert aggregated.coverage_matrix.tested_scenarios == 0


def test_analyze_project_failing_analyzer_is_dropped(monkeypatch, tmp_path, capsys):
    ok = _FakeAnalyzer(_result(ProjectType.REST_API, ["/a"]))
    broken = _FakeAnalyzer(error=RuntimeError("boom"))
    router = _router_with(monkeypatch, tmp_path, [ok, broken])

    report = router.analyze_project(tmp_path, verbose=True, use_cache=False)

    assert list(report["results"]) == ["rest_api"]
    assert "failed: boom" in capsys.readouterr().out


def test_analyze_project_second_run_served_from_cache(monkeypatch, tmp_path, capsys):
    (tmp_path / "main.py").write_text("x = 1\n")
    analyzer = _FakeAnalyzer(_result(ProjectType.REST_API, ["/a"]))
    router = _router_with(monkeypatch, tmp_path, [analyzer])

    first = router.analyze_project(tmp_path, use_cache=True)
    second = router.analyze_project(tmp_path, verbose=True, use_cache=True)

    assert analyzer.calls == 1
    assert first["cache"] == {"enabled": True, "hits": 0, "misses": 1}
    assert second["cache"] == {"enabled": True, "hits": 1, "misses": 0}
    assert second["summary"] == first["summary"]
    assert "loaded from cache" in capsys.readouterr().out


def test_analyze_project_verbose_prints_phases(monkeypatch, tmp_path, capsys):
    api = _FakeAnalyzer(_result(ProjectType.REST_API, ["/a"]))
    cli = _FakeAnalyzer(_result(ProjectType.CLI_APP, ["run"]))
    router = _router_with(monkeypatch, tmp_path, [api, cli], types=(ProjectType.REST_API, ProjectType.CLI_APP))

    router.analyze_project(tmp_path, verbose=True, use_cache=False)

    out = capsys.readouterr().out
    assert "Phase 0" in out and "Language: python" in out
    assert "_FakeAnalyzer: 1 entry points, 1 scenarios" in out
    assert "Phase 5" in out
    assert "Analysis complete!" in out
