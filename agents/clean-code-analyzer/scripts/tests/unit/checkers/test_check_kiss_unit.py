"""Unit tests for checkers/check_kiss.py — mocks complexity subprocess and Ollama."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import checkers.check_kiss as kiss_mod
from checkers.check_kiss import run

HIGH_COMPLEXITY_OUTPUT = json.dumps({
    "files_analyzed": 1,
    "complexity_issues": [
        {
            "file": "app.py",
            "function": "process_data",
            "cyclomatic_complexity": 15,
            "nesting_depth": 4,
            "lines": 80,
            "severity": "high",
        }
    ],
})

LOW_COMPLEXITY_OUTPUT = json.dumps({
    "files_analyzed": 1,
    "complexity_issues": [],
})


@pytest.fixture
def mocked_calc_complexity():
    """Patch _CALC_COMPLEXITY to claim it exists."""
    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path:
        mock_path.exists.return_value = True
        yield mock_path


@pytest.mark.unit
def test_kiss_high_complexity_creates_violation(tmp_path, mocked_calc_complexity):
    """High-complexity function → KISS violation created from subprocess output."""
    (tmp_path / "app.py").write_text("def process_data(): pass\n")

    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr=""
        )
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) >= 1
    assert any(v["principle"] == "KISS" for v in result["violations"])


@pytest.mark.unit
def test_kiss_low_complexity_no_violation(tmp_path, mocked_calc_complexity):
    """Low complexity → no complexity violations."""
    (tmp_path / "app.py").write_text("def simple(): return 1\n")

    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr=""
        )
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_kiss_ollama_called_only_when_available(tmp_path, mocked_calc_complexity):
    """Ollama analyze_files_parallel is only called when check_ollama_available=True."""
    (tmp_path / "app.py").write_text("class Foo: pass\n")

    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=True), \
         patch.object(kiss_mod, "analyze_files_parallel", return_value=[]) as mock_ollama:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr=""
        )
        run(tmp_path, "python")

    mock_ollama.assert_called_once()


@pytest.mark.unit
def test_kiss_subprocess_failure_graceful(tmp_path):
    """Subprocess failure → graceful empty result, success=True (complexity part skipped)."""
    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, \
         patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_kiss_subprocess_timeout_graceful(tmp_path):
    """subprocess.TimeoutExpired → graceful empty result (exception path)."""
    import subprocess
    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)), \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_path.exists.return_value = True
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_kiss_subprocess_json_decode_error_graceful(tmp_path):
    """subprocess returns invalid JSON → JSONDecodeError caught, empty violations."""
    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, \
         patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="{ invalid json }", stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_kiss_incremental_files_filter_by_name(tmp_path, mocked_calc_complexity):
    """In incremental mode (files=[...]), complexity issues are filtered to changed files."""
    targeted = tmp_path / "targeted.py"
    targeted.write_text("def process_data(): pass\n")
    other = tmp_path / "other.py"
    other.write_text("def simple(): pass\n")

    # Subprocess returns violations for both files but only targeted is in incremental list
    both_files_output = json.dumps({
        "files_analyzed": 2,
        "complexity_issues": [
            {"file": "targeted.py", "function": "process_data", "cyclomatic_complexity": 15,
             "nesting_depth": 4, "lines": 80, "severity": "high"},
            {"file": "other.py", "function": "simple", "cyclomatic_complexity": 15,
             "nesting_depth": 4, "lines": 80, "severity": "high"},
        ],
    })
    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=both_files_output, stderr="")
        result = run(tmp_path, "python", files=[targeted])

    # Only targeted.py violation should be included
    for v in result["violations"]:
        assert "targeted" in v["file"] or "targeted" in v.get("file", "")


@pytest.mark.unit
def test_kiss_ollama_violation_appended(tmp_path, mocked_calc_complexity):
    """Ollama returns violation → appended to violations list with principle=KISS."""
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    def get_user(self): pass\n")

    ollama_item = {
        "source_file": str(f),
        "source_file_name": f.name,
        "pattern": "OverEngineering",
        "violation": "Over-abstracted service",
        "severity": "medium",
        "suggestion": "Simplify",
        "line": 1,
    }
    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=True), \
         patch.object(kiss_mod, "analyze_files_parallel", return_value=[ollama_item]):
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=None)

    kiss_v = [v for v in result["violations"] if v["principle"] == "KISS"]
    assert len(kiss_v) >= 1
    assert "OverEngineering" in kiss_v[0]["message"]


@pytest.mark.unit
def test_kiss_files_not_none_ollama_path(tmp_path, mocked_calc_complexity):
    """files is not None + Ollama available → line 68 (source_files filter from files list)."""
    f = tmp_path / "service.py"
    f.write_text("class X: pass\n")

    with patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=True), \
         patch.object(kiss_mod, "analyze_files_parallel", return_value=[]) as mock_ollama:
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=[f])

    mock_ollama.assert_called_once()
    assert result["success"] is True


@pytest.mark.unit
def test_kiss_files_analyzed_zero_gets_set_from_source_files(tmp_path):
    """files_analyzed=0 after complexity part → set from source_files (line 75)."""
    f = tmp_path / "service.py"
    f.write_text("class X: pass\n")

    # Return output with files_analyzed=0 to leave files_analyzed=0 after complexity
    empty_output = json.dumps({"files_analyzed": 0, "complexity_issues": []})
    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, \
         patch("subprocess.run") as mock_run, \
         patch.object(kiss_mod, "check_ollama_available", return_value=True), \
         patch.object(kiss_mod, "discover_files", return_value=[f]), \
         patch.object(kiss_mod, "analyze_files_parallel", return_value=[]):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=empty_output, stderr="")
        result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    assert result["files_analyzed"] >= 1  # set from source_files (line 75)
