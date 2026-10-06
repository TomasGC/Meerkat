#!/usr/bin/env python3
"""Tests for library_analyzer.py — unit tests"""

import subprocess
from unittest.mock import MagicMock, patch

import library_analyzer
from bba.models import HTTPMethod, ProjectType
from library_analyzer import (
    LibraryAnalyzer,
    _branch_to_scenario,
    _infer_scenario_type,
    _risk_for_scenario,
    _run_script,
)


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


def test_can_analyze_no_detected_types():
    project_info = MagicMock()
    project_info.endpoint_count = 0
    project_info.project_types = []
    project_info.metadata = {}
    assert LibraryAnalyzer().can_analyze(project_info) is True


def test_cannot_analyze_zero_endpoints_with_detected_type():
    """A CLI or Android project serves no HTTP but is not a library."""
    project_info = MagicMock()
    project_info.endpoint_count = 0
    project_info.project_types = [ProjectType.CLI_APP]
    project_info.metadata = {}
    assert LibraryAnalyzer().can_analyze(project_info) is False


def test_can_analyze_is_library_flag():
    project_info = MagicMock()
    project_info.endpoint_count = 5
    project_info.project_types = [ProjectType.REST_API]
    project_info.metadata = {"is_library": True}
    assert LibraryAnalyzer().can_analyze(project_info) is True


def test_cannot_analyze_has_endpoints_no_flag():
    project_info = MagicMock()
    project_info.endpoint_count = 3
    project_info.project_types = [ProjectType.REST_API]
    project_info.metadata = {}
    assert LibraryAnalyzer().can_analyze(project_info) is False


# ── _run_script ───────────────────────────────────────────────────────────────


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_script_parses_json_stdout():
    with patch.object(library_analyzer.subprocess, "run", return_value=_completed(0, '{"methods": []}')) as run:
        assert _run_script("analyze_library_branches.py", "src", "--language", "go") == {"methods": []}
    cmd = run.call_args.args[0]
    assert cmd[1].endswith("analyze_library_branches.py")
    assert cmd[2:] == ["src", "--language", "go"]


def test_run_script_nonzero_exit_returns_none(capsys):
    with patch.object(library_analyzer.subprocess, "run", return_value=_completed(1, "", "model offline")):
        assert _run_script("scan_tdd_refactoring.py") is None
    assert "exited 1: model offline" in capsys.readouterr().err


def test_run_script_invalid_json_returns_none(capsys):
    with patch.object(library_analyzer.subprocess, "run", return_value=_completed(0, "not json")):
        assert _run_script("scan_tdd_refactoring.py") is None
    assert "scan_tdd_refactoring.py failed" in capsys.readouterr().err


def test_run_script_timeout_returns_none():
    timeout = subprocess.TimeoutExpired(cmd="x", timeout=300)
    with patch.object(library_analyzer.subprocess, "run", side_effect=timeout):
        assert _run_script("scan_tdd_refactoring.py") is None


def test_risk_for_scenario_edge_case_scores_27():
    scenario = _branch_to_scenario({"method": "fn"}, {"condition": "empty list", "outcome": "returns 0"}, 0)
    risk = _risk_for_scenario(scenario)
    assert risk.risk_score == 27
    assert risk.reasoning.startswith("Library branch: ")
