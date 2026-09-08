"""Tests for checkers/check_integ_mock_gaps.py"""

from pathlib import Path
from unittest.mock import patch

from checkers.check_integ_mock_gaps import run


def test_run_returns_contract_keys(tmp_path):
    (tmp_path / "repo.py").write_text("def save(db, obj): pass", encoding="utf-8")
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert {"principle", "success", "violations", "files_analyzed", "duration_ms"} <= result.keys()
    assert result["principle"] == "INTEG_MOCK_GAP"
    assert result["success"] is True


def test_run_no_violations_when_mock_test_exists(tmp_path):
    (tmp_path / "repo.py").write_text("def save(db, obj): pass", encoding="utf-8")
    mock_dir = tmp_path / "tests" / "integration" / "mock"
    mock_dir.mkdir(parents=True)
    (mock_dir / "test_repo.py").write_text("def test_save(): pass", encoding="utf-8")
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["violations"] == []


def test_run_violation_when_no_mock_test(tmp_path):
    (tmp_path / "repo.py").write_text("def save(db, obj): pass", encoding="utf-8")
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert len(result["violations"]) == 1
    assert result["violations"][0]["principle"] == "INTEG_MOCK_GAP"


def test_run_model_results_include_interaction_type(tmp_path):
    (tmp_path / "repo.py").write_text("def save(db, obj): db.insert(obj)", encoding="utf-8")
    model_output = [{
        "source_file": str(tmp_path / "repo.py"),
        "source_file_name": "repo.py",
        "function": "save",
        "line": 1,
        "severity": "high",
        "interaction_type": "database",
        "reason": "inserts into database without mock test",
        "test_scenario": "test save with mocked DB returning success and error",
    }]
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=True), \
         patch("checkers.check_integ_mock_gaps.analyze_files_parallel", return_value=model_output):
        result = run(tmp_path, "python")
    assert "database" in result["violations"][0]["message"]
    assert "save" in result["violations"][0]["message"]


def test_run_respects_files_filter(tmp_path):
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python", files=[tmp_path / "a.py"])
    assert result["files_analyzed"] == 1


def test_run_fallback_suggestion_mentions_tier(tmp_path):
    (tmp_path / "svc.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert "integration/mock" in result["violations"][0]["suggestion"]


def test_run_duration_ms_non_negative(tmp_path):
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["duration_ms"] >= 0
