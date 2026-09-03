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
