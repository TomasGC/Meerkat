#!/usr/bin/env python3
"""Tests for analyzers/event_driven/base_event_driven_analyzer.py: shared event-driven scenario generation."""

from collections import Counter
from pathlib import Path

from analyzers.event_driven.base_event_driven_analyzer import BaseEventDrivenAnalyzer
from bba.models import EntryPoint, EntryPointType, ProjectInfo, TestCase


class _StubEventAnalyzer(BaseEventDrivenAnalyzer):
    """Minimal concrete subclass: the base only adds scenario generation."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        return True

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        return []

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        return []


def _handler(name: str) -> EntryPoint:
    return EntryPoint(EntryPointType.MESSAGE_CONSUMER, name, [], "h.py", 1)


def test_each_entry_point_gets_the_full_event_driven_scenario_set():
    scenarios = _StubEventAnalyzer().generate_scenarios([_handler("orders.consume")])

    assert len(scenarios) == 17
    assert {s.endpoint for s in scenarios} == {"orders.consume"}
    assert {s.method_name for s in scenarios} == {"EVENT"}
    assert Counter(s.scenario_type for s in scenarios) == {"happy_path": 2, "edge_case": 7, "error": 8}
    assert scenarios[0].description == "Process valid event in orders.consume"


def test_scenarios_cover_retry_timeout_dlq_validation_and_async_concerns():
    descriptions = [s.description for s in _StubEventAnalyzer().generate_scenarios([_handler("job")])]

    for fragment in (
        "max retries exceeded",
        "execution timeout",
        "move to DLQ",
        "malformed event payload",
        "rate limit exceeded",
        "batch event processing",
    ):
        assert any(fragment in d for d in descriptions), fragment


def test_scenarios_scale_linearly_with_entry_points_and_empty_input_gives_none():
    analyzer = _StubEventAnalyzer()

    assert analyzer.generate_scenarios([]) == []
    assert len(analyzer.generate_scenarios([_handler("a"), _handler("b")])) == 34


def test_failure_scenarios_expect_non_zero_outcome():
    scenarios = _StubEventAnalyzer().generate_scenarios([_handler("job")])

    by_desc = {s.description: s.expected_output for s in scenarios}
    assert by_desc["job max retries exceeded"] == 1
    assert by_desc["job completes within timeout"] == 0
    assert by_desc["job process message from DLQ"] == 0
