"""Tests for checkers/check_e2e_gaps.py"""

from pathlib import Path
from unittest.mock import patch

from checkers.check_e2e_gaps import run


def test_run_returns_contract_keys(tmp_path):
    (tmp_path / "api.py").write_text("def create_user(): pass", encoding="utf-8")
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert {"principle", "success", "violations", "files_analyzed", "duration_ms"} <= result.keys()
    assert result["principle"] == "E2E_GAP"
    assert result["success"] is True


def test_run_no_violations_when_e2e_test_exists(tmp_path):
    (tmp_path / "api.py").write_text("def create_user(): pass", encoding="utf-8")
    e2e_dir = tmp_path / "tests" / "e2e"
    e2e_dir.mkdir(parents=True)
    (e2e_dir / "test_api.py").write_text("def test_create_user_flow(): pass", encoding="utf-8")
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["violations"] == []


def test_run_violation_when_no_e2e_test(tmp_path):
    (tmp_path / "api.py").write_text("def create_user(): pass", encoding="utf-8")
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert len(result["violations"]) == 1
    assert result["violations"][0]["principle"] == "E2E_GAP"


def test_run_model_results_include_flow_type(tmp_path):
    (tmp_path / "api.py").write_text("@app.post('/users')\ndef create_user(): pass", encoding="utf-8")
    model_output = [{
        "source_file": str(tmp_path / "api.py"),
        "source_file_name": "api.py",
        "function": "create_user",
        "line": 2,
        "severity": "high",
        "flow_type": "api_endpoint",
        "reason": "POST /users is the main user registration flow",
        "test_scenario": "test full registration flow: POST /users → GET /users/{id} → verify",
    }]
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=True), \
         patch("checkers.check_e2e_gaps.analyze_files_parallel", return_value=model_output):
        result = run(tmp_path, "python")
    assert "api_endpoint" in result["violations"][0]["message"]
    assert "create_user" in result["violations"][0]["message"]


def test_run_respects_files_filter(tmp_path):
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python", files=[tmp_path / "a.py"])
    assert result["files_analyzed"] == 1


def test_run_fallback_suggestion_mentions_e2e(tmp_path):
    (tmp_path / "svc.py").write_text("pass", encoding="utf-8")
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert "e2e" in result["violations"][0]["suggestion"]


def test_run_duration_ms_non_negative(tmp_path):
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["duration_ms"] >= 0
