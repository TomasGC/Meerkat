#!/usr/bin/env python3
"""Tests for analyze_code_patterns.py"""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.analyze_code_patterns import AnalyzeCodePatternsScript


@pytest.fixture
def script():
    """Create script instance."""
    return AnalyzeCodePatternsScript()


@pytest.fixture
def temp_project(tmp_path):
    """Create temp project with various code quality issues."""
    # File with dead code
    (tmp_path / "dead.py").write_text("""
def used_function():
    return 1

def unused_function():
    return 2

result = used_function()
""")

    # File with duplicate code
    (tmp_path / "dup1.py").write_text("""
def process(data):
    result = []
    for x in data:
        result.append(x * 2)
    return result
""")

    (tmp_path / "dup2.py").write_text("""
def transform(values):
    output = []
    for x in values:
        output.append(x * 2)
    return output
""")

    return tmp_path


def test_run_dead_code_check(script, temp_project, monkeypatch):
    """Test dead code check execution."""
    result = script._run_dead_code_check(temp_project)

    assert result is not None
    assert "unused_symbols" in result or "error" in result


def test_run_dry_check(script, temp_project, monkeypatch):
    """Test DRY violations check execution."""
    result = script._run_dry_check(temp_project)

    assert result is not None
    assert "duplicates" in result or "error" in result


def test_run_complexity_check(script, temp_project, monkeypatch):
    """Test complexity check execution."""
    result = script._run_complexity_check(temp_project)

    assert result is not None
    assert "complexity_issues" in result or "error" in result


def test_script_execution_success(script, temp_project, monkeypatch):
    """Test full script execution."""

    class Args:
        path = temp_project
        checks = "dead_code,dry,complexity"
        use_ollama = False

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert "dead_code" in result
    assert "dry_violations" in result
    assert "complexity_issues" in result
    assert "total_issues" in result


def test_script_selective_checks(script, temp_project, monkeypatch):
    """Test execution with selective checks."""

    class Args:
        path = temp_project
        checks = "dead_code"
        use_ollama = False

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert result["checks_performed"] == ["dead_code"]


class TestModelResolution:
    """Verify get_model() is used for model selection in _ask_ollama_dead_code."""

    def test_ask_ollama_uses_get_model_with_fast_role(self, tmp_path):
        """_ask_ollama_dead_code calls get_model('fast', ...) to resolve the model name."""
        from unittest.mock import MagicMock, patch

        import cli.analyze_code_patterns as mod

        item = {"name": "unused_fn", "file": "mod.py"}
        instance = AnalyzeCodePatternsScript()

        captured_roles = []

        def fake_get_model(role, provider="local", fallback=None):
            captured_roles.append(role)
            return fallback or "test-model"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "yes"

        with patch.object(mod, "_get_model", fake_get_model):
            with patch("cli.analyze_code_patterns.subprocess.run", return_value=mock_result):
                instance._ask_ollama_dead_code(item)

        assert "fast" in captured_roles, "get_model should be called with role='fast'"


# ── behaviour with the helper scripts mocked ─────────────────────────────────


def _args(path, checks="smells", use_ollama=False):
    return argparse.Namespace(path=path, checks=checks, use_ollama=use_ollama)


def test_execute_rejects_missing_path(script, tmp_path):
    result = script.execute(_args(tmp_path / "absent"))
    assert result["success"] is False
    assert result["error"].startswith("Path not found")


def test_execute_collects_each_helper_result(script, tmp_path):
    answers = {
        "find_unused_code.py": {"unused_symbols": [{"name": "f"}]},
        "find_duplicates.py": {"duplicates": [{"a": 1}, {"b": 2}]},
        "calculate_complexity.py": {"complexity_issues": [{"c": 3}]},
    }

    def run(cmd, **_kwargs):
        return 0, json.dumps(answers[Path(cmd[1]).name]), ""

    with patch("cli.analyze_code_patterns.run_command", side_effect=run):
        result = script.execute(_args(tmp_path, checks="dead_code,dry,complexity"))

    assert result["dead_code"] == [{"name": "f"}]
    assert len(result["dry_violations"]) == 2
    assert result["complexity_issues"] == [{"c": 3}]
    assert result["total_issues"] == 4
    assert result["estimated_token_savings"] == 5000 + 4 * 300


@pytest.mark.parametrize("answer", [(1, "", "crash"), (0, "not json", "")])
def test_helper_failure_or_bad_json_yields_none(script, tmp_path, answer):
    with patch("cli.analyze_code_patterns.run_command", return_value=answer):
        assert script._run_dead_code_check(tmp_path) is None
        assert script._run_dry_check(tmp_path) is None
        assert script._run_complexity_check(tmp_path) is None


def test_missing_helper_script_yields_none(script, tmp_path):
    with patch.object(Path, "exists", return_value=False):
        assert script._run_dead_code_check(tmp_path) is None
        assert script._run_dry_check(tmp_path) is None
        assert script._run_complexity_check(tmp_path) is None


def test_detect_code_smells_flags_magic_numbers_but_not_http_codes(script, tmp_path):
    (tmp_path / "m.py").write_text("TIMEOUT = 3600\nOK = 200\nx = 42\n", encoding="utf-8")

    smells = script._detect_code_smells(tmp_path)

    assert smells == [
        {
            "file": "m.py",
            "type": "magic_number",
            "value": "3600",
            "line": 1,
            "severity": "medium",
            "suggestion": "Extract to named constant",
        }
    ]


def test_detect_code_smells_on_single_file_and_limit(script, tmp_path):
    target = tmp_path / "big.py"
    target.write_text("\n".join(f"v{i} = {1000 + i}" for i in range(30)), encoding="utf-8")

    smells = script._detect_code_smells(target)

    assert len(smells) == 20
    assert smells[0]["file"] == "big.py"


def test_detect_code_smells_skips_unreadable_files(script, tmp_path):
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe 9999")
    assert script._detect_code_smells(tmp_path) == []


def test_ollama_validation_skipped_when_unavailable(script):
    results = {"dead_code": [{"name": "f", "file": "a.py", "confidence": "low"}]}
    with patch("cli.analyze_code_patterns.run_command", return_value=(1, "", "")):
        assert script._validate_with_ollama(results) is results
    assert results["dead_code"][0]["confidence"] == "low"


def test_ollama_validation_keeps_confirmed_low_confidence_items(script):
    results = {
        "dead_code": [
            {"name": "sure", "file": "a.py", "confidence": "high"},
            {"name": "confirmed", "file": "a.py", "confidence": "low"},
            {"name": "rejected", "file": "a.py", "confidence": "low"},
        ]
    }
    with patch("cli.analyze_code_patterns.run_command", return_value=(0, "", "")), patch.object(
        script, "_ask_ollama_dead_code", side_effect=[True, False]
    ):
        validated = script._validate_with_ollama(results)

    assert [(i["name"], i["confidence"]) for i in validated["dead_code"]] == [
        ("sure", "high"),
        ("confirmed", "medium"),
    ]


def test_execute_with_ollama_flag_validates(script, tmp_path):
    with patch.object(script, "_validate_with_ollama", side_effect=lambda r: r) as validate:
        script.execute(_args(tmp_path, use_ollama=True))
    validate.assert_called_once()


@pytest.mark.parametrize(
    "outcome,expected",
    [
        (MagicMock(returncode=0, stdout="Yes, unused"), True),
        (MagicMock(returncode=0, stdout="no"), False),
        (MagicMock(returncode=1, stdout="yes"), False),
        (OSError("no ollama"), False),
    ],
)
def test_ask_ollama_dead_code_reads_answer(script, outcome, expected):
    kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
    with patch("cli.analyze_code_patterns.subprocess.run", **kwargs):
        assert script._ask_ollama_dead_code({"name": "f", "file": "a.py"}) is expected
