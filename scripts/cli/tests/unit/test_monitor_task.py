"""Unit tests for LocalAIMonitor in monitor_task.py — all subprocess calls mocked."""

import importlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

_MODULE = "cli.agents.task_monitor.monitor_task"

# monitor_task calls get_model at import time: stub model_config for the import
# only, so the stub never leaks into the other suites sharing this process.
importlib.import_module("lib.config")  # parent packages stay imported after the patch
importlib.import_module("cli.agents.task_monitor")
_fake_mc = types.ModuleType("lib.config.model_config")
_fake_mc.get_model = lambda role, *a, **kw: f"test-model-{role}"  # type: ignore[attr-defined]
with patch.dict(sys.modules, {"lib.config.model_config": _fake_mc}):
    sys.modules.pop(_MODULE, None)
    monitor_task = importlib.import_module(_MODULE)

_DEFAULT_MODEL = monitor_task._DEFAULT_MODEL
LocalAIMonitor = monitor_task.LocalAIMonitor
TaskMonitor = monitor_task.TaskMonitor

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

    with patch.object(monitor_task.subprocess, "run", return_value=mock_result):
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

    with patch.object(monitor_task.subprocess, "run", return_value=mock_result):
        result = monitor.analyze_log("log content", "build", {})

    assert result["status"] == "success"


# ── LocalAIMonitor.analyze_log: fallback paths ───────────────────────────────


def test_analyze_log_fallback_when_returncode_nonzero():
    """analyze_log falls back to _fallback_analysis when subprocess returns non-zero."""
    monitor = LocalAIMonitor(model="test-model")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with patch.object(monitor_task.subprocess, "run", return_value=mock_result):
        result = monitor.analyze_log("BUILD FAILED: error", "build", {})

    assert "status" in result
    assert "problem_detected" in result


def test_analyze_log_fallback_on_exception():
    """analyze_log falls back to _fallback_analysis when subprocess raises."""
    monitor = LocalAIMonitor(model="test-model")

    with patch.object(monitor_task.subprocess, "run", side_effect=OSError("not found")):
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


# ── LocalAIMonitor._build_analysis_prompt ────────────────────────────────────


def test_build_analysis_prompt_lists_criteria_and_keeps_log_tail():
    prompt = LocalAIMonitor(model="m")._build_analysis_prompt("x" * 20000 + "TAIL", "build", {"stall": "120s"})
    assert prompt.startswith("Analyze this build log")
    assert "- stall: 120s" in prompt
    assert "TAIL" in prompt
    assert "x" * 10001 not in prompt  # only the last ~10KB of the log


def test_analyze_log_without_json_in_answer_falls_back():
    answer = MagicMock(returncode=0, stdout="no json here")
    with patch.object(monitor_task.subprocess, "run", return_value=answer):
        result = LocalAIMonitor(model="m").analyze_log("BUILD SUCCESSFUL", "build", {})
    assert result["status"] == "success"


# ── TaskMonitor ──────────────────────────────────────────────────────────────

_CLEAN = {"status": "running", "problem_detected": False, "summary": "ok", "details": {}}


def _monitor(tmp_path, log_text="line 1\n", **kwargs):
    log = tmp_path / "task.log"
    log.write_text(log_text, encoding="utf-8")
    monitor = TaskMonitor(
        pid=kwargs.pop("pid", 123),
        log_file=log,
        task_type=kwargs.pop("task_type", "test"),
        output_file=tmp_path / "note.txt",
        poll_interval=0,
        **kwargs,
    )
    monitor.ollama = MagicMock()
    return monitor


def test_is_process_running_uses_psutil_for_pid(tmp_path):
    fake_psutil = types.SimpleNamespace(pid_exists=lambda pid: pid == 123)
    with patch.dict(sys.modules, {"psutil": fake_psutil}):
        assert _monitor(tmp_path)._is_process_running() is True
        assert _monitor(tmp_path, pid=7)._is_process_running() is False


def test_is_process_running_falls_back_to_ps_without_psutil(tmp_path):
    with patch.dict(sys.modules, {"psutil": None}):
        with patch.object(monitor_task.subprocess, "run", return_value=MagicMock(returncode=1)) as run:
            assert _monitor(tmp_path)._is_process_running() is False
    assert run.call_args[0][0] == ["ps", "-p", "123"]


def test_is_process_running_by_pattern_uses_pgrep(tmp_path):
    monitor = _monitor(tmp_path, pid=None, pattern="gradle.*test")
    with patch.object(monitor_task.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
        assert monitor._is_process_running() is True
    assert run.call_args[0][0] == ["pgrep", "-f", "gradle.*test"]


def test_read_log_missing_file_is_empty(tmp_path):
    monitor = _monitor(tmp_path)
    monitor.log_file = tmp_path / "absent.log"
    assert monitor._read_log() == ""


def test_is_stalled_only_after_threshold_without_growth(tmp_path):
    monitor = _monitor(tmp_path, stall_threshold=5)
    with patch.object(monitor_task.time, "time", return_value=1000.0):
        assert monitor._is_stalled("abc") is False  # size changed: timer reset
    with patch.object(monitor_task.time, "time", return_value=1004.0):
        assert monitor._is_stalled("abc") is False
    with patch.object(monitor_task.time, "time", return_value=1006.0):
        assert monitor._is_stalled("abc") is True


def test_detection_criteria_per_task_type(tmp_path):
    assert _monitor(tmp_path, task_type="deploy")._get_detection_criteria()["success"] == "Deployment complete"
    assert _monitor(tmp_path, task_type="generic")._get_detection_criteria() == {}


def test_monitor_writes_completed_notification_when_process_ends(tmp_path):
    monitor = _monitor(tmp_path)
    monitor.ollama.analyze_log.return_value = {
        "status": "success",
        "problem_detected": False,
        "summary": "All 12 tests passed",
        "details": {
            "errors": ["e1"],
            "warnings": ["w1"],
            "affected_files": ["a.py"],
            "suggestions": ["s1"],
        },
    }
    with patch.object(monitor, "_is_process_running", return_value=False):
        monitor.monitor()

    note = (tmp_path / "note.txt").read_text(encoding="utf-8")
    assert "Event: COMPLETED" in note
    assert "Status: SUCCESS" in note
    assert "Summary: All 12 tests passed" in note
    for section in ("Errors:\n  - e1", "Warnings:\n  - w1", "Affected Files:\n  - a.py", "Suggestions:\n  - s1"):
        assert section in note


def test_monitor_stops_on_detected_problem(tmp_path):
    monitor = _monitor(tmp_path)
    monitor.ollama.analyze_log.side_effect = [
        _CLEAN,
        {"status": "failed", "problem_detected": True, "summary": "NPE"},
    ]
    with patch.object(monitor, "_is_process_running", return_value=True), patch.object(
        monitor, "_is_stalled", return_value=False
    ), patch.object(monitor_task.time, "sleep") as sleep:
        monitor.monitor()

    note = (tmp_path / "note.txt").read_text(encoding="utf-8")
    assert "Event: PROBLEM" in note and "Summary: NPE" in note
    sleep.assert_called_once_with(0)


def test_monitor_reports_stall(tmp_path):
    monitor = _monitor(tmp_path)
    monitor.ollama.analyze_log.return_value = dict(_CLEAN)
    with patch.object(monitor, "_is_process_running", return_value=True), patch.object(
        monitor, "_is_stalled", return_value=True
    ):
        monitor.monitor()

    assert monitor.ollama.analyze_log.call_args[0][2] == {"stall_detected": True}
    note = (tmp_path / "note.txt").read_text(encoding="utf-8")
    assert "Event: STALLED" in note and "Status: STALLED" in note


def test_monitor_records_user_interrupt(tmp_path):
    monitor = _monitor(tmp_path)
    with patch.object(monitor, "_is_process_running", side_effect=KeyboardInterrupt):
        monitor.monitor()
    note = (tmp_path / "note.txt").read_text(encoding="utf-8")
    assert "Event: INTERRUPTED" in note and "User cancelled monitoring" in note


def test_monitor_records_unexpected_error(tmp_path):
    monitor = _monitor(tmp_path)
    with patch.object(monitor, "_is_process_running", side_effect=RuntimeError("ps exploded")):
        monitor.monitor()
    note = (tmp_path / "note.txt").read_text(encoding="utf-8")
    assert "Event: ERROR" in note and "Summary: ps exploded" in note


def test_main_requires_pid_or_pattern(tmp_path, capsys):
    with patch.object(sys, "argv", ["monitor_task.py", "--log", str(tmp_path / "x.log")]):
        with pytest.raises(SystemExit) as exc:
            monitor_task.main()
    assert exc.value.code == 2
    assert "Either --pid or --pattern" in capsys.readouterr().err


def test_main_builds_monitor_from_arguments(tmp_path):
    argv = ["monitor_task.py", "--pid", "42", "--log", str(tmp_path / "x.log"), "--type", "build", "--interval", "3"]
    with patch.object(sys, "argv", argv), patch.object(TaskMonitor, "monitor", autospec=True) as run:
        monitor_task.main()
    built = run.call_args[0][0]
    assert (built.pid, built.task_type, built.poll_interval) == (42, "build", 3)
