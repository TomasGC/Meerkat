"""Unit tests for common/hybrid.py — the shared mechanical-then-AI driver."""
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.hybrid import resolve_language, run_hybrid, scan_patterns, select_files

_RULES = {
    "python": [(re.compile(r'\bdanger\b'), "Danger called", "high", "Stop calling danger")],
    "*": [(re.compile(r'\bTODO\b'), "Leftover marker", "low", "Resolve or track it")],
}


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestResolveLanguage:
    def test_explicit_language_wins(self, tmp_path):
        assert resolve_language(tmp_path / "a.py", "python") == "python"

    def test_mixed_resolved_by_extension(self, tmp_path):
        assert resolve_language(tmp_path / "Service.cs", "mixed") == "csharp"

    def test_unknown_extension_returns_unknown(self, tmp_path):
        assert resolve_language(tmp_path / "notes.txt", "mixed") == "unknown"

    def test_dockerfile_recognised_by_name(self, tmp_path):
        assert resolve_language(tmp_path / "Dockerfile", "mixed") == "dockerfile"

    def test_dockerfile_variant_recognised(self, tmp_path):
        assert resolve_language(tmp_path / "Dockerfile.prod", "python") == "dockerfile"


class TestSelectFiles:
    def test_explicit_files_filtered_by_extension(self, tmp_path):
        keep = _make_file(tmp_path, "a.py", "x = 1\n")
        drop = _make_file(tmp_path, "notes.txt", "hello\n")
        assert select_files(tmp_path, "python", [keep, drop]) == [keep]

    def test_discovery_skips_test_files(self, tmp_path):
        _make_file(tmp_path, "service.py", "x = 1\n")
        _make_file(tmp_path, "test_service.py", "x = 1\n")
        found = [f.name for f in select_files(tmp_path, "python", None)]
        assert found == ["service.py"]

    def test_empty_directory_returns_empty(self, tmp_path):
        assert select_files(tmp_path, "python", None) == []


class TestScanPatterns:
    def test_language_rule_matches(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert [v["message"] for v in violations] == ["Danger called"]

    def test_universal_rule_applies_to_every_language(self, tmp_path):
        f = _make_file(tmp_path, "Service.cs", "// TODO later\n")
        violations = scan_patterns(f, tmp_path, "csharp", "Test", _RULES)
        assert [v["message"] for v in violations] == ["Leftover marker"]

    def test_line_numbers_are_one_based(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\ndanger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert violations[0]["line"] == 2

    def test_paths_are_relative_to_root(self, tmp_path):
        nested = tmp_path / "src"
        nested.mkdir()
        f = nested / "a.py"
        f.write_text("danger()\n")
        violations = scan_patterns(f, tmp_path, "python", "Test", _RULES)
        assert violations[0]["file"] == str(Path("src") / "a.py")

    def test_language_without_rules_returns_empty(self, tmp_path):
        empty_rules = {"python": _RULES["python"]}
        f = _make_file(tmp_path, "main.go", "package main\n")
        assert scan_patterns(f, tmp_path, "go", "Test", empty_rules) == []

    def test_missing_file_returns_empty(self, tmp_path):
        assert scan_patterns(tmp_path / "gone.py", tmp_path, "python", "Test", _RULES) == []

    def test_violation_carries_principle_and_suggestion(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        violation = scan_patterns(f, tmp_path, "python", "Test", _RULES)[0]
        assert violation["principle"] == "Test"
        assert violation["severity"] == "high"
        assert violation["suggestion"] == "Stop calling danger"


class TestRunHybrid:
    def test_returns_checker_contract(self, tmp_path):
        with patch("common.hybrid.check_server_available", return_value=False):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES)
        assert result["principle"] == "Test"
        assert result["success"] is True
        assert result["violations"] == []
        assert result["files_analyzed"] == 0
        assert "duration_ms" in result

    def test_mechanical_findings_reported_without_server(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        with patch("common.hybrid.check_server_available", return_value=False):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert [v["message"] for v in result["violations"]] == ["Danger called"]

    def test_ai_findings_appended(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "issue_type": "SOMETHING", "line": 1,
                     "severity": "low", "description": "detail", "fix": "do this"}
        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert result["violations"][0]["message"] == "[SOMETHING]: detail"
        assert result["violations"][0]["suggestion"] == "do this"

    def test_ai_type_key_is_configurable(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "leak_type": "UNCLOSED_HANDLE", "line": 1,
                     "description": "detail", "fix": ""}
        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES,
                                files=[f], ai_type_key="leak_type")
        assert result["violations"][0]["message"].startswith("[UNCLOSED_HANDLE]")

    def test_default_severity_applied_when_absent(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "x = 1\n")
        fake_item = {"source_file": str(f), "issue_type": "X", "line": 1, "description": "d", "fix": ""}
        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES,
                                files=[f], default_severity="high")
        assert result["violations"][0]["severity"] == "high"

    def test_ai_finding_near_mechanical_one_dropped(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        fake_item = {"source_file": str(f), "issue_type": "DUP", "line": 2,
                     "description": "same thing", "fix": ""}
        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel", return_value=[fake_item]):
            result = run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert [v["message"] for v in result["violations"]] == ["Danger called"]

    def test_known_findings_slot_carries_mechanical_messages(self, tmp_path):
        f = _make_file(tmp_path, "a.py", "danger()\n")
        captured = {}

        def fake_analyze(files, *args, **kwargs):
            captured["extra_slots"] = kwargs.get("extra_slots")
            return []

        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel", side_effect=fake_analyze):
            run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[f])
        assert "Danger called" in captured["extra_slots"][f]["known_findings"]

    def test_ai_not_called_when_no_files(self, tmp_path):
        with patch("common.hybrid.check_server_available", return_value=True), \
             patch("common.hybrid.analyze_files_parallel") as analyze:
            run_hybrid(tmp_path, "python", "Test", "prompt", _RULES, files=[])
        analyze.assert_not_called()
