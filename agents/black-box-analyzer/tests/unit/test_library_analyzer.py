#!/usr/bin/env python3
"""Tests for library_analyzer.py — unit tests"""

from pathlib import Path
from unittest.mock import MagicMock

from library_analyzer import (
    LibraryAnalyzer,
    _branch_to_scenario,
    _infer_scenario_type,
    _risk_for_scenario,
)
from common.models import HTTPMethod, ProjectType

def test_infer_scenario_type_error_raises_keyword():
    branch = {"condition": "valid arg", "outcome": "raises ValueError on invalid input"}
    assert _infer_scenario_type(branch) == "error"

def test_infer_scenario_type_error_throw_keyword():
    branch = {"condition": "any", "outcome": "throws RuntimeException"}
    assert _infer_scenario_type(branch) == "error"

def test_infer_scenario_type_edge_case_null():
    branch = {"condition": "null input provided", "outcome": "returns empty list"}
    assert _infer_scenario_type(branch) == "edge_case"

def test_infer_scenario_type_edge_case_empty():
    branch = {"condition": "empty string argument", "outcome": "returns default"}
    assert _infer_scenario_type(branch) == "edge_case"

def test_infer_scenario_type_happy_path():
    branch = {"condition": "valid data", "outcome": "returns processed result"}
    assert _infer_scenario_type(branch) == "happy_path"

def test_branch_to_scenario_endpoint_from_method_name():
    method = {"method": "parse_config", "signature": "def parse_config(path)"}
    branch = {"condition": "valid path", "outcome": "returns dict", "test_scenario": "parse valid config"}
    scenario = _branch_to_scenario(method, branch, 0)
    assert scenario.endpoint == "parse_config"

def test_branch_to_scenario_sentinel_http_get():
    method = {"method": "my_func"}
    branch = {"condition": "any", "outcome": "returns result", "test_scenario": "normal call"}
    scenario = _branch_to_scenario(method, branch, 0)
    assert scenario.method == HTTPMethod.GET

def test_branch_to_scenario_description_from_test_scenario():
    method = {"method": "fn"}
    branch = {"condition": "c", "outcome": "o", "test_scenario": "the expected description"}
    scenario = _branch_to_scenario(method, branch, 0)
    assert scenario.description == "the expected description"

def test_branch_to_scenario_type_inferred_edge_case():
    method = {"method": "fn"}
    branch = {"condition": "null arg", "outcome": "returns none", "test_scenario": "null case"}
    scenario = _branch_to_scenario(method, branch, 0)
    assert scenario.scenario_type == "edge_case"

def test_risk_for_scenario_error_scores_48():
    method = {"method": "fn"}
    branch = {"condition": "any", "outcome": "raises Exception", "test_scenario": "error case"}
    scenario = _branch_to_scenario(method, branch, 0)
    risk = _risk_for_scenario(scenario)
    assert risk.technical_risk == 4
    assert risk.failure_probability == 4
    assert risk.risk_score == 48

def test_risk_for_scenario_happy_path_scores_12():
    method = {"method": "fn"}
    branch = {"condition": "valid input", "outcome": "returns result", "test_scenario": "happy case"}
    scenario = _branch_to_scenario(method, branch, 0)
    risk = _risk_for_scenario(scenario)
    assert risk.technical_risk == 2
    assert risk.failure_probability == 2
    assert risk.risk_score == 12

def test_can_analyze_zero_endpoints():
    project_info = MagicMock()
    project_info.endpoint_count = 0
    project_info.metadata = {}
    assert LibraryAnalyzer().can_analyze(project_info) is True

def test_can_analyze_is_library_flag():
    project_info = MagicMock()
    project_info.endpoint_count = 5
    project_info.metadata = {"is_library": True}
    assert LibraryAnalyzer().can_analyze(project_info) is True

def test_cannot_analyze_has_endpoints_no_flag():
    project_info = MagicMock()
    project_info.endpoint_count = 3
    project_info.metadata = {}
    assert LibraryAnalyzer().can_analyze(project_info) is False
