"""Unit tests for check_concurrency — mechanical patterns plus mocked AI layer."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers.check_concurrency import run, _mechanical_check, _PRINCIPLE


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestMechanicalCSharp:
    def test_detects_mutable_static_field(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "    private static Dictionary<string, int> _hits = new();\n")
        violations = _mechanical_check(f, tmp_path, "csharp")
        assert any("Mutable static field" in v["message"] for v in violations)

    def test_readonly_static_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "    private static readonly object _gate = new();\n")
        assert _mechanical_check(f, tmp_path, "csharp") == []

    def test_detects_lock_on_this(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "        lock (this)\n")
        violations = _mechanical_check(f, tmp_path, "csharp")
        assert any("publicly reachable" in v["message"] for v in violations)

    def test_lock_on_private_gate_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "        lock (_gate)\n")
        assert _mechanical_check(f, tmp_path, "csharp") == []


class TestMechanicalGo:
    def test_detects_waitgroup_add_inside_goroutine(self, tmp_path):
        code = "go func() {\n\twg.Add(1)\n\tdefer wg.Done()\n}()\n"
        f = _make_file(tmp_path, "worker.go", code)
        violations = _mechanical_check(f, tmp_path, "go")
        assert any("WaitGroup.Add" in v["message"] for v in violations)

    def test_add_before_goroutine_is_clean(self, tmp_path):
        code = "wg.Add(1)\ngo func() {\n\tdefer wg.Done()\n}()\n"
        f = _make_file(tmp_path, "worker.go", code)
        assert _mechanical_check(f, tmp_path, "go") == []

    def test_detects_sleep_as_synchronization(self, tmp_path):
        f = _make_file(tmp_path, "worker.go", "\ttime.Sleep(100 * time.Millisecond)\n")
        violations = _mechanical_check(f, tmp_path, "go")
        assert any("Sleep used" in v["message"] for v in violations)


class TestMechanicalSharedState:
    def test_detects_global_in_threaded_python(self, tmp_path):
        code = "import threading\n\ndef bump():\n    global counter\n    counter += 1\n"
        f = _make_file(tmp_path, "worker.py", code)
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("Global mutated" in v["message"] for v in violations)

    def test_global_without_threading_is_ignored(self, tmp_path):
        code = "def bump():\n    global counter\n    counter += 1\n"
        f = _make_file(tmp_path, "worker.py", code)
        assert _mechanical_check(f, tmp_path, "python") == []

    def test_detects_global_write_in_powershell_job(self, tmp_path):
        code = "Start-ThreadJob { $global:total = 1 }\n"
        f = _make_file(tmp_path, "run.ps1", code)
        violations = _mechanical_check(f, tmp_path, "powershell")
        assert any("Global variable written" in v["message"] for v in violations)

    def test_unreadable_file_returns_empty(self, tmp_path):
        missing = tmp_path / "gone.cs"
        assert _mechanical_check(missing, tmp_path, "csharp") == []


class TestReconciliation:
    def test_mechanical_violations_reported_without_server(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "    private static int _hits = 0;\n")
        with patch("checkers.check_concurrency.check_server_available", return_value=False):
            result = run(tmp_path, "csharp", files=[f])
        assert result["violations"]
        assert result["success"] is True

    def test_ai_finding_near_mechanical_one_dropped(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "    private static int _hits = 0;\n")
        fake_item = {
            "source_file": str(f),
            "issue_type": "RACE_CONDITION",
            "line": 1,
            "severity": "high",
            "description": "Static counter is not thread safe",
            "fix": "Use Interlocked",
        }
        with patch("checkers.check_concurrency.check_server_available", return_value=True), \
             patch("checkers.check_concurrency.analyze_files_parallel", return_value=[fake_item]):
            result = run(tmp_path, "csharp", files=[f])
        assert not any(v["message"].startswith("[") for v in result["violations"])

    def test_known_findings_slot_passed_to_ai(self, tmp_path):
        f = _make_file(tmp_path, "Cache.cs", "    private static int _hits = 0;\n")
        captured = {}

        def fake_analyze(files, *args, **kwargs):
            captured["extra_slots"] = kwargs.get("extra_slots")
            return []

        with patch("checkers.check_concurrency.check_server_available", return_value=True), \
             patch("checkers.check_concurrency.analyze_files_parallel", side_effect=fake_analyze):
            run(tmp_path, "csharp", files=[f])
        assert "Mutable static field" in captured["extra_slots"][f]["known_findings"]


class TestRunFunction:
    def test_returns_correct_schema(self, tmp_path):
        with patch("checkers.check_concurrency.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["principle"] == _PRINCIPLE
        assert result["success"] is True
        assert "violations" in result
        assert "files_analyzed" in result
        assert "duration_ms" in result

    def test_no_server_returns_empty_not_error(self, tmp_path):
        _make_file(tmp_path, "service.py", "x = 1\n")
        with patch("checkers.check_concurrency.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["success"] is True
        assert result["violations"] == []
        assert "error" not in result

    def test_with_server_calls_analyze(self, tmp_path):
        _make_file(tmp_path, "worker.go", 'package main\nvar counter int\n')
        fake_item = {
            "source_file": str(tmp_path / "worker.go"),
            "issue_type": "RACE_CONDITION",
            "line": 2,
            "severity": "high",
            "description": "Shared counter accessed without lock",
            "fix": "Use sync/atomic or mutex",
        }
        with patch("checkers.check_concurrency.check_server_available", return_value=True), \
             patch("checkers.check_concurrency.analyze_files_parallel", return_value=[fake_item]):
            result = run(tmp_path, "go")
        assert len(result["violations"]) == 1
        assert result["violations"][0]["principle"] == _PRINCIPLE
        assert "RACE_CONDITION" in result["violations"][0]["message"]

    def test_files_kwarg_passed_through(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x=1\n")
        captured = {}
        def fake_analyze(files, *args, **kwargs):
            captured["files"] = files
            return []
        with patch("checkers.check_concurrency.check_server_available", return_value=True), \
             patch("checkers.check_concurrency.analyze_files_parallel", side_effect=fake_analyze):
            run(tmp_path, "python", files=[f])
        assert captured.get("files") == [f]
