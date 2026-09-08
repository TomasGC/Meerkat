"""Tests for checkers/check_integ_real_gaps.py"""

from pathlib import Path
from unittest.mock import patch

from checkers.check_integ_real_gaps import run


def test_run_returns_contract_keys(tmp_path):
    (tmp_path / "db.py").write_text("def query(conn): pass", encoding="utf-8")
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert {"principle", "success", "violations", "files_analyzed", "duration_ms"} <= result.keys()
    assert result["principle"] == "INTEG_REAL_GAP"
    assert result["success"] is True


def test_run_no_violations_when_real_test_exists(tmp_path):
    (tmp_path / "db.py").write_text("def query(conn): pass", encoding="utf-8")
    real_dir = tmp_path / "tests" / "integration" / "real"
    real_dir.mkdir(parents=True)
    (real_dir / "test_db.py").write_text("def test_query(): pass", encoding="utf-8")
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["violations"] == []


def test_run_violation_when_no_real_test(tmp_path):
    (tmp_path / "db.py").write_text("def query(conn): pass", encoding="utf-8")
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert len(result["violations"]) == 1
    assert result["violations"][0]["principle"] == "INTEG_REAL_GAP"


def test_run_model_results_include_operation_type(tmp_path):
    (tmp_path / "db.py").write_text("def query(conn): return conn.execute('SELECT ...')", encoding="utf-8")
    model_output = [{
        "source_file": str(tmp_path / "db.py"),
        "source_file_name": "db.py",
        "function": "query",
        "line": 1,
        "severity": "high",
        "operation_type": "db_query",
        "reason": "complex SQL join needs real DB semantics",
        "test_scenario": "test query against real PostgreSQL with fixture data",
    }]
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=True), \
         patch("checkers.check_integ_real_gaps.analyze_files_parallel", return_value=model_output):
        result = run(tmp_path, "python")
    assert "db_query" in result["violations"][0]["message"]
    assert "query" in result["violations"][0]["message"]


def test_run_respects_files_filter(tmp_path):
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python", files=[tmp_path / "a.py"])
    assert result["files_analyzed"] == 1


def test_run_fallback_suggestion_mentions_tier(tmp_path):
    (tmp_path / "svc.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert "integration/real" in result["violations"][0]["suggestion"]


def test_run_duration_ms_non_negative(tmp_path):
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["duration_ms"] >= 0
