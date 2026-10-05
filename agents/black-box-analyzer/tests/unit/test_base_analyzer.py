#!/usr/bin/env python3
"""Tests for analyzers/base_analyzer.py: the shared coverage, risk and pipeline logic."""

from pathlib import Path

from analyzers.base_analyzer import BaseAnalyzer
from bba.models import (
    AnalysisResult,
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    Language,
    ProjectInfo,
    ProjectType,
    Scenario,
    TestCase,
    TestFramework,
)


def _scenario(endpoint: str, scenario_type: str, method="GET") -> Scenario:
    return Scenario(
        endpoint=endpoint,
        method=HTTPMethod(method) if method in HTTPMethod._value2member_map_ else method,
        input_combination={},
        expected_output=200,
        scenario_type=scenario_type,
    )


def _test(name: str, tested_endpoint: str | None = None, test_type: str = "unit") -> TestCase:
    return TestCase(
        name=name,
        file_path="tests/test_x.py",
        line_number=1,
        framework=TestFramework.PYTEST,
        tested_endpoint=tested_endpoint,
        test_type=test_type,
    )


class _StubAnalyzer(BaseAnalyzer):
    """Concrete analyzer with fixed outputs, so only the base class logic is exercised."""

    def __init__(self, entry_points, tests, scenarios):
        self._entry_points = entry_points
        self._tests = tests
        self._scenarios = scenarios
        self.calls: list[str] = []

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        return True

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        self.calls.append("extract")
        return self._entry_points

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        self.calls.append("parse")
        return self._tests

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        self.calls.append("scenarios")
        return self._scenarios


def _analyzer(scenarios=(), tests=(), entry_points=()) -> _StubAnalyzer:
    return _StubAnalyzer(list(entry_points), list(tests), list(scenarios))


# ── generate_coverage_matrix ──────────────────────────────────────────────────


def test_coverage_matrix_matches_test_by_tested_endpoint_case_insensitively():
    matrix = _analyzer().generate_coverage_matrix(
        [_scenario("/Users", "happy_path"), _scenario("/orders", "happy_path")],
        [_test("test_list_users", tested_endpoint="/users")],
    )

    assert matrix.total_scenarios == 2
    assert matrix.tested_scenarios == 1
    assert matrix.untested_scenarios == 1
    assert matrix.coverage_percent == 50.0
    tested_gap, untested_gap = matrix.gaps
    assert tested_gap.is_tested and [t.name for t in tested_gap.related_tests] == ["test_list_users"]
    assert not untested_gap.is_tested and untested_gap.related_tests == []


def test_coverage_matrix_matches_test_whose_type_equals_scenario_type():
    matrix = _analyzer().generate_coverage_matrix(
        [_scenario("/a", "security")], [_test("test_whatever", test_type="security")]
    )

    assert matrix.tested_scenarios == 1


def test_coverage_matrix_matches_test_named_after_method():
    matrix = _analyzer().generate_coverage_matrix(
        [_scenario("do_it", "happy_path", method="EXECUTE")], [_test("EXECUTE")]
    )

    assert matrix.gaps[0].is_tested


def test_coverage_matrix_with_no_scenarios_reports_zero_percent():
    matrix = _analyzer().generate_coverage_matrix([], [_test("test_a")])

    assert (matrix.total_scenarios, matrix.coverage_percent, matrix.gaps) == (0, 0.0, [])


def test_extract_keywords_of_unknown_object_is_empty():
    assert _analyzer()._extract_keywords(object()) == set()


# ── calculate_risks ───────────────────────────────────────────────────────────


def test_calculate_risks_scores_each_scenario_type_and_sorts_highest_first():
    scenarios = [
        _scenario("/perf", "performance"),
        _scenario("/edge", "edge_case"),
        _scenario("/ok", "happy_path"),
        _scenario("/err", "error"),
        _scenario("/sec", "security"),
    ]
    analyzer = _analyzer()
    risks = analyzer.calculate_risks(analyzer.generate_coverage_matrix(scenarios, []))

    summary = [(r.gap.scenario.endpoint, r.risk_score, r.risk_level) for r in risks]
    assert summary == [
        ("/sec", 125, "CRITICAL"),
        ("/err", 48, "HIGH"),
        ("/ok", 27, "MEDIUM"),
        ("/edge", 24, "MEDIUM"),
        ("/perf", 18, "LOW"),
    ]
    security = risks[0]
    assert (security.business_impact, security.technical_risk, security.failure_probability) == (5, 5, 5)
    assert security.reasoning == "CRITICAL risk: security scenario for '/sec' is not tested"


def test_calculate_risks_skips_tested_scenarios():
    analyzer = _analyzer()
    matrix = analyzer.generate_coverage_matrix(
        [_scenario("/users", "error"), _scenario("/orders", "error")],
        [_test("t", tested_endpoint="/users")],
    )

    risks = analyzer.calculate_risks(matrix)

    assert [r.gap.scenario.endpoint for r in risks] == ["/orders"]


# ── analyze ───────────────────────────────────────────────────────────────────


def test_analyze_runs_the_pipeline_in_order_and_assembles_the_result(tmp_path):
    entry = EntryPoint(type=EntryPointType.HTTP_ENDPOINT, name="GET /users", params=[], file_path="a.py", line_number=3)
    scenarios = [_scenario("/users", "happy_path"), _scenario("/users-admin", "security")]
    tests = [_test("t", tested_endpoint="/users")]
    analyzer = _analyzer(scenarios=scenarios, tests=tests, entry_points=[entry])
    info = ProjectInfo(
        language=Language.PYTHON,
        frameworks=[],
        endpoint_count=1,
        test_file_count=1,
        root_path=str(tmp_path),
        project_types=[ProjectType.REST_API],
        primary_type=ProjectType.REST_API,
    )

    result = analyzer.analyze(tmp_path, info)

    assert isinstance(result, AnalysisResult)
    assert analyzer.calls == ["extract", "parse", "scenarios"]
    assert result.project_type == ProjectType.REST_API
    assert result.entry_points == [entry]
    assert result.test_cases == tests
    assert result.scenarios == scenarios
    assert result.coverage_matrix.tested_scenarios == 1
    assert [r.gap.scenario.endpoint for r in result.risk_assessment] == ["/users-admin"]
