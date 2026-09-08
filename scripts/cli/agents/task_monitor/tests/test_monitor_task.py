"""Unit tests for LocalAIMonitor in monitor_task.py — all subprocess calls mocked."""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load monitor_task module with model_config.get_model mocked so we don't hit disk
_MONITOR_DIR = Path(__file__).parent.parent  # scripts/cli/agents/task_monitor/
_SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent.parent  # ~/.claude/scripts
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_MONITOR_DIR))

# Stub model_config before the module is imported (it calls get_model at import time)
_fake_mc = types.ModuleType("model_config")
_fake_mc.get_model = lambda role, *a, **kw: f"test-model-{role}"
sys.modules["model_config"] = _fake_mc
sys.modules.pop("monitor_task", None)

# Now safe to import
from monitor_task import LocalAIMonitor, _DEFAULT_MODEL  # noqa: E402


# ── _DEFAULT_MODEL resolved via get_model("fast") ────────────────────────────

def test_default_model_resolved_from_config():
    """_DEFAULT_MODEL is resolved via get_model('fast'), not a hardcoded string."""
    # Our stub returns "test-model-fast", confirming get_model was called with "fast"
    assert _DEFAULT_MODEL == "test-model-fast"


# ── LocalAIMonitor.analyze_log: success path ─────────────────────────────────

def test_analyze_log_success_returns_parsed_json():
    """analyze_log returns dict from JSON when subprocess succeeds."""
    monitor = LocalAIMonitor(model="test-model")
    expected = {
        "status": "running",
        "problem_detected": False,
        "summary": "All clear",
        "details": {"errors": [], "warnings": [], "affected_files": [], "suggestions": []},
    }
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(expected)

    with patch("monitor_task.subprocess.run", return_value=mock_result):
        result = monitor.analyze_log("some log", "test", {})

    assert result["status"] == "running"
    assert result["problem_detected"] is False
    assert result["summary"] == "All clear"


def test_analyze_log_success_extracts_json_block_from_prose():
    """analyze_log extracts JSON block even when surrounded by prose."""
    monitor = LocalAIMonitor(model="test-model")
    inner = {"status": "success", "problem_detected": False, "summary": "Done", "details": {}}
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = f"Here is my analysis:\n{json.dumps(inner)}\nEnd of analysis."

    with patch("monitor_task.subprocess.run", return_value=mock_result):
        result = monitor.analyze_log("log content", "build", {})

    assert result["status"] == "success"


# ── LocalAIMonitor.analyze_log: fallback paths ───────────────────────────────

def test_analyze_log_fallback_when_returncode_nonzero():
    """analyze_log falls back to _fallback_analysis when subprocess returns non-zero."""
    monitor = LocalAIMonitor(model="test-model")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with patch("monitor_task.subprocess.run", return_value=mock_result):
        result = monitor.analyze_log("BUILD FAILED: error", "build", {})

    assert "status" in result
    assert "problem_detected" in result


def test_analyze_log_fallback_on_exception():
    """analyze_log falls back to _fallback_analysis when subprocess raises."""
    monitor = LocalAIMonitor(model="test-model")

    with patch("monitor_task.subprocess.run", side_effect=OSError("not found")):
        result = monitor.analyze_log("some log", "test", {})

    assert "status" in result
    assert "problem_detected" in result


# ── LocalAIMonitor._fallback_analysis ────────────────────────────────────────

def test_fallback_analysis_detects_build_failure():
    """_fallback_analysis sets status='failed' and problem_detected=True on BUILD FAILED."""
    monitor = LocalAIMonitor(model="test-model")
    log = "Compiling...\nBUILD FAILED: compilation error at Main.java:42\nerror: cannot find symbol"

    result = monitor._fallback_analysis(log, "build")

    assert result["status"] == "failed"
    assert result["problem_detected"] is True
    assert len(result["details"]["errors"]) > 0


def test_fallback_analysis_detects_build_success():
    """_fallback_analysis sets status='success' on BUILD SUCCESSFUL."""
    monitor = LocalAIMonitor(model="test-model")
    log = "Compiling...\nBUILD SUCCESSFUL in 3s"

    result = monitor._fallback_analysis(log, "build")

    assert result["status"] == "success"
    assert result["problem_detected"] is False


def test_fallback_analysis_detects_error_keyword():
    """_fallback_analysis detects 'error:' pattern and sets problem_detected=True."""
    monitor = LocalAIMonitor(model="test-model")
    log = "Running tests...\nError: NullPointerException at line 99"

    result = monitor._fallback_analysis(log, "test")

    assert result["problem_detected"] is True
    assert result["status"] == "failed"


def test_fallback_analysis_running_when_clean():
    """_fallback_analysis returns status='running' when no error/success patterns found."""
    monitor = LocalAIMonitor(model="test-model")
    log = "Compiling module A...\nCompiling module B...\n"

    result = monitor._fallback_analysis(log, "build")

    assert result["status"] == "running"
    assert result["problem_detected"] is False
    assert result["details"]["errors"] == []


def test_fallback_analysis_result_has_required_keys():
    """_fallback_analysis always returns dict with status/problem_detected/summary/details."""
    monitor = LocalAIMonitor(model="test-model")
    result = monitor._fallback_analysis("any log", "generic")
    assert "status" in result
    assert "problem_detected" in result
    assert "summary" in result
    assert "details" in result
