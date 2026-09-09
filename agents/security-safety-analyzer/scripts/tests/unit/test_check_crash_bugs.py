"""Unit tests for check_crash_bugs — mechanical AST path only (AI mocked out)."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers.check_crash_bugs import run, _check_python_file, _pattern_check, _PRINCIPLE


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestCheckPythonFile:
    def test_detects_division_by_variable(self, tmp_path):
        f = _make_file(tmp_path, "calc.py", "result = total / count\n")
        violations = _check_python_file(f, tmp_path)
        assert any("div" in v["message"].lower() or "zero" in v["message"].lower() for v in violations)

    def test_no_violation_on_literal_divisor(self, tmp_path):
        f = _make_file(tmp_path, "calc.py", "result = total / 2\n")
        violations = _check_python_file(f, tmp_path)
        assert violations == []

    def test_detects_subscript_without_guard(self, tmp_path):
        f = _make_file(tmp_path, "parser.py", "first = items[0]\n")
        violations = _check_python_file(f, tmp_path)
        assert any("bound" in v["message"].lower() or "index" in v["message"].lower() or
                   "subscript" in v["message"].lower() for v in violations)

    def test_syntax_error_returns_empty(self, tmp_path):
        f = _make_file(tmp_path, "bad.py", "def bad(:\n")
        violations = _check_python_file(f, tmp_path)
        assert violations == []


class TestPatternCheckCSharp:
    def test_detects_parse(self, tmp_path):
        f = _make_file(tmp_path, "Parser.cs", "var age = int.Parse(input);\n")
        violations = _pattern_check(f, tmp_path, "csharp")
        assert any("TryParse" in v["suggestion"] for v in violations)

    def test_detects_first_without_default(self, tmp_path):
        f = _make_file(tmp_path, "Repo.cs", "var user = users.First();\n")
        violations = _pattern_check(f, tmp_path, "csharp")
        assert any("empty" in v["message"] for v in violations)

    def test_detects_member_access_after_as_cast(self, tmp_path):
        f = _make_file(tmp_path, "Repo.cs", "var name = (obj as User).Name;\n")
        violations = _pattern_check(f, tmp_path, "csharp")
        assert any("NullReferenceException" in v["message"] for v in violations)

    def test_safe_csharp_is_clean(self, tmp_path):
        code = "if (int.TryParse(input, out var age))\n{\n    Use(age);\n}\n"
        f = _make_file(tmp_path, "Parser.cs", code)
        assert _pattern_check(f, tmp_path, "csharp") == []


class TestPatternCheckGo:
    def test_detects_type_assertion_without_ok(self, tmp_path):
        f = _make_file(tmp_path, "main.go", "\tuser := value.(User)\n")
        violations = _pattern_check(f, tmp_path, "go")
        assert any("comma-ok" in v["message"] for v in violations)

    def test_comma_ok_assertion_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "main.go", "\tuser, ok := value.(User)\n")
        assert _pattern_check(f, tmp_path, "go") == []


class TestPatternCheckJsTs:
    def test_detects_json_parse(self, tmp_path):
        f = _make_file(tmp_path, "api.ts", "const data = JSON.parse(body);\n")
        violations = _pattern_check(f, tmp_path, "typescript")
        assert any("JSON.parse" in v["message"] for v in violations)

    def test_detects_non_null_assertion(self, tmp_path):
        f = _make_file(tmp_path, "api.ts", "const name = user!.name;\n")
        violations = _pattern_check(f, tmp_path, "typescript")
        assert any("Non-null assertion" in v["message"] for v in violations)

    def test_detects_parse_int_without_radix(self, tmp_path):
        f = _make_file(tmp_path, "api.js", "const n = parseInt(raw);\n")
        violations = _pattern_check(f, tmp_path, "javascript")
        assert any("radix" in v["message"] for v in violations)

    def test_parse_int_with_radix_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "api.js", "const n = parseInt(raw, 10);\n")
        assert _pattern_check(f, tmp_path, "javascript") == []


class TestPatternCheckShells:
    def test_detects_hard_cast_powershell(self, tmp_path):
        f = _make_file(tmp_path, "run.ps1", "$count = [int]$env:COUNT\n")
        violations = _pattern_check(f, tmp_path, "powershell")
        assert any("Hard cast" in v["message"] for v in violations)

    def test_detects_rm_rf_on_variable(self, tmp_path):
        f = _make_file(tmp_path, "clean.sh", 'rm -rf "$TARGET"\n')
        violations = _pattern_check(f, tmp_path, "bash")
        assert any("rm -rf" in v["message"] for v in violations)

    def test_unknown_language_returns_empty(self, tmp_path):
        f = _make_file(tmp_path, "conf.yaml", "key: value\n")
        assert _pattern_check(f, tmp_path, "yaml") == []


class TestNonPythonIntegration:
    def test_pattern_violations_reported_without_server(self, tmp_path):
        f = _make_file(tmp_path, "Parser.cs", "var age = int.Parse(input);\n")
        with patch("checkers.check_crash_bugs.check_server_available", return_value=False):
            result = run(tmp_path, "csharp", files=[f])
        assert result["violations"]
        assert all(v["principle"] == _PRINCIPLE for v in result["violations"])

    def test_ai_findings_near_pattern_findings_dropped(self, tmp_path):
        f = _make_file(tmp_path, "Parser.cs", "var age = int.Parse(input);\n")
        fake_item = {
            "source_file": str(f),
            "bug_type": "TYPE_ERROR",
            "line": 1,
            "severity": "high",
            "description": "Parse can throw",
            "fix": "Use TryParse",
        }
        with patch("checkers.check_crash_bugs.check_server_available", return_value=True), \
             patch("checkers.check_crash_bugs.analyze_files_parallel", return_value=[fake_item]):
            result = run(tmp_path, "csharp", files=[f])
        assert not any(v["message"].startswith("[") for v in result["violations"])

    def test_distant_ai_findings_kept(self, tmp_path):
        code = "var age = int.Parse(input);\n" + "\n" * 20 + "Use(age);\n"
        f = _make_file(tmp_path, "Parser.cs", code)
        fake_item = {
            "source_file": str(f),
            "bug_type": "NULL_DEREF",
            "line": 22,
            "severity": "high",
            "description": "age may be null",
            "fix": "Check for null",
        }
        with patch("checkers.check_crash_bugs.check_server_available", return_value=True), \
             patch("checkers.check_crash_bugs.analyze_files_parallel", return_value=[fake_item]):
            result = run(tmp_path, "csharp", files=[f])
        assert any(v["message"].startswith("[NULL_DEREF]") for v in result["violations"])

    def test_known_findings_slot_passed_to_ai(self, tmp_path):
        f = _make_file(tmp_path, "Parser.cs", "var age = int.Parse(input);\n")
        captured = {}

        def fake_analyze(files, *args, **kwargs):
            captured["extra_slots"] = kwargs.get("extra_slots")
            return []

        with patch("checkers.check_crash_bugs.check_server_available", return_value=True), \
             patch("checkers.check_crash_bugs.analyze_files_parallel", side_effect=fake_analyze):
            run(tmp_path, "csharp", files=[f])
        assert "TryParse" in captured["extra_slots"][f]["known_findings"]


class TestRunFunction:
    def test_returns_correct_schema(self, tmp_path):
        with patch("checkers.check_crash_bugs.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["principle"] == _PRINCIPLE
        assert result["success"] is True
        assert "violations" in result
        assert "files_analyzed" in result

    def test_empty_dir_no_violations(self, tmp_path):
        with patch("checkers.check_crash_bugs.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["violations"] == []

    def test_files_kwarg_limits_scope(self, tmp_path):
        f = _make_file(tmp_path, "safe.py", "x = 1\n")
        with patch("checkers.check_crash_bugs.check_server_available", return_value=False):
            result = run(tmp_path, "python", files=[f])
        assert result["files_analyzed"] <= 1
