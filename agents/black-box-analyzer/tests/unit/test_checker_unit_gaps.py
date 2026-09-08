"""Tests for checkers/check_unit_gaps.py"""

from pathlib import Path
from unittest.mock import patch

from checkers.check_unit_gaps import run


def test_run_returns_contract_keys(tmp_path):
    (tmp_path / "app.py").write_text("def foo(): pass", encoding="utf-8")
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert {"principle", "success", "violations", "files_analyzed", "duration_ms"} <= result.keys()
    assert result["principle"] == "UNIT_GAP"
    assert result["success"] is True
    assert isinstance(result["violations"], list)
    assert isinstance(result["files_analyzed"], int)
    assert isinstance(result["duration_ms"], int)


def test_run_no_violations_when_unit_test_exists(tmp_path):
    (tmp_path / "foo.py").write_text("def foo(): pass", encoding="utf-8")
    unit_dir = tmp_path / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    (unit_dir / "test_foo.py").write_text("def test_foo(): pass", encoding="utf-8")
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["violations"] == []


def test_run_violation_when_no_test_server_unavailable(tmp_path):
    (tmp_path / "bar.py").write_text("def bar(): pass", encoding="utf-8")
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert len(result["violations"]) == 1
    assert result["violations"][0]["principle"] == "UNIT_GAP"


def test_run_model_results_mapped_to_violations(tmp_path):
    (tmp_path / "svc.py").write_text("def process(x): return x * 2", encoding="utf-8")
    model_output = [{
        "source_file": str(tmp_path / "svc.py"),
        "source_file_name": "svc.py",
        "function": "process",
        "line": 1,
        "severity": "high",
        "reason": "non-trivial computation",
        "test_scenario": "test process with zero and negative inputs",
    }]
    with patch("checkers.check_unit_gaps.check_server_available", return_value=True), \
         patch("checkers.check_unit_gaps.analyze_files_parallel", return_value=model_output):
        result = run(tmp_path, "python")
    assert len(result["violations"]) == 1
    assert result["violations"][0]["severity"] == "high"
    assert "process" in result["violations"][0]["message"]


def test_run_respects_files_filter(tmp_path):
    (tmp_path / "a.py").write_text("def a(): pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("def b(): pass", encoding="utf-8")
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python", files=[tmp_path / "a.py"])
    assert result["files_analyzed"] == 1


def test_run_fallback_violation_has_suggestion(tmp_path):
    (tmp_path / "svc.py").write_text("def svc(): pass", encoding="utf-8")
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["violations"][0]["suggestion"] != ""


def test_run_duration_ms_non_negative(tmp_path):
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["duration_ms"] >= 0
