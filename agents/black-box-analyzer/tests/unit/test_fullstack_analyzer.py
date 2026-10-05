#!/usr/bin/env python3
"""Tests for analyzers/fullstack_analyzer.py: API + frontend analysis combined."""

import pytest
from analyzers.fullstack_analyzer import FullstackAnalyzer
from bba.models import (
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    Language,
    ProjectInfo,
    ProjectType,
    TestCase,
    TestFramework,
)


def _info(*types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.TYPESCRIPT,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=".",
        project_types=list(types),
    )


def _entry(entry_type: EntryPointType, name: str, metadata=None) -> EntryPoint:
    return EntryPoint(
        type=entry_type, name=name, params=[], file_path="f.ts", line_number=1, metadata=dict(metadata or {})
    )


class _Fixed:
    """Stand-in sub-analyzer returning fixed entry points and tests."""

    def __init__(self, entry_points=(), tests=()):
        self._entry_points = list(entry_points)
        self._tests = list(tests)

    def extract_entry_points(self, project_path):
        return self._entry_points

    def parse_tests(self, project_path):
        return self._tests


def test_can_analyze_only_fullstack_projects():
    assert FullstackAnalyzer().can_analyze(_info(ProjectType.FULLSTACK))
    assert not FullstackAnalyzer().can_analyze(_info(ProjectType.FRONTEND_REACT))


def test_extract_entry_points_concatenates_api_then_frontend(tmp_path):
    api_entry = _entry(EntryPointType.HTTP_ENDPOINT, "GET /api/users")
    component = _entry(EntryPointType.COMPONENT, "UserList")
    analyzer = FullstackAnalyzer()
    analyzer.api_analyzer = _Fixed(entry_points=[api_entry])
    analyzer.frontend_analyzer = _Fixed(entry_points=[component])

    assert analyzer.extract_entry_points(tmp_path) == [api_entry, component]


def test_parse_tests_concatenates_api_and_frontend_tests(tmp_path):
    api_test = TestCase(name="api", file_path="a", line_number=1, framework=TestFramework.JEST)
    ui_test = TestCase(name="ui", file_path="b", line_number=1, framework=TestFramework.JEST)
    analyzer = FullstackAnalyzer()
    analyzer.api_analyzer = _Fixed(tests=[api_test])
    analyzer.frontend_analyzer = _Fixed(tests=[ui_test])

    assert analyzer.parse_tests(tmp_path) == [api_test, ui_test]


def test_extract_entry_points_on_express_project_finds_the_api_routes(sample_typescript_project):
    entry_points = FullstackAnalyzer().extract_entry_points(sample_typescript_project)

    http = sorted(ep.name for ep in entry_points if ep.type == EntryPointType.HTTP_ENDPOINT)
    assert http == ["DELETE /api/posts/:id", "GET /api/posts/:id", "POST /api/posts"]


def test_generate_scenarios_gives_endpoints_api_scenarios_and_components_render_scenarios():
    api_entry = _entry(EntryPointType.HTTP_ENDPOINT, "POST /users", {"method": "POST", "path": "/users"})
    component = _entry(EntryPointType.COMPONENT, "UserList")

    scenarios = FullstackAnalyzer().generate_scenarios([api_entry, component])

    endpoint_scenarios = [s for s in scenarios if s.endpoint == "/users"]
    assert [s.expected_output for s in endpoint_scenarios] == [200, 400, 401]
    assert {s.method for s in endpoint_scenarios} == {HTTPMethod.POST}
    assert "RENDER" in {s.method for s in scenarios if s.endpoint == "UserList"}


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): "
    "APIAnalyzer.generate_scenarios defaults a missing method to GET, so components get HTTP scenarios",
)
def test_generate_scenarios_gives_components_no_http_scenarios():
    scenarios = FullstackAnalyzer().generate_scenarios([_entry(EntryPointType.COMPONENT, "UserList")])

    assert not [s for s in scenarios if isinstance(s.method, HTTPMethod)]
