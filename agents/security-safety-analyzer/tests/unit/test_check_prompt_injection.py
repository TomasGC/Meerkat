"""Unit tests for check_prompt_injection — mechanical path only (AI mocked out)."""
from pathlib import Path
from unittest.mock import patch

import pytest


from ssa.checkers.check_prompt_injection import run, _mechanical_check, _PRINCIPLE


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


class TestMechanicalCheck:
    def test_detects_fstring_user_input(self, tmp_path):
        code = 'prompt = f"Answer the user: {user_message}"\n'
        f = _make_file(tmp_path, "agent.py", code)
        violations = _mechanical_check(f, tmp_path, "python")
        assert len(violations) >= 1
        assert violations[0]["severity"] == "high"

    def test_detects_format_with_input(self, tmp_path):
        code = 'prompt = template.format(content=request.body)\n'
        f = _make_file(tmp_path, "handler.py", code)
        violations = _mechanical_check(f, tmp_path, "python")
        assert len(violations) >= 1

    def test_clean_python_no_violations(self, tmp_path):
        code = 'prompt = f"Answer based on context: {document_chunk}"\n'
        f = _make_file(tmp_path, "safe.py", code)
        violations = _mechanical_check(f, tmp_path, "python")
        assert violations == []

    def test_detects_js_template_literal(self, tmp_path):
        code = 'const prompt = `User says: ${userInput}`;\n'
        f = _make_file(tmp_path, "api.ts", code)
        violations = _mechanical_check(f, tmp_path, "typescript")
        assert len(violations) >= 1

    def test_detects_prompt_file_raw_slot(self, tmp_path):
        f = _make_file(tmp_path, "system.prompt", "Answer the following: {user_input}\n")
        violations = _mechanical_check(f, tmp_path, "unknown")
        assert len(violations) >= 1
        assert violations[0]["severity"] == "medium"

    def test_no_violation_safe_prompt_file(self, tmp_path):
        f = _make_file(tmp_path, "safe.prompt", "Analyze the code: {code}\n")
        violations = _mechanical_check(f, tmp_path, "unknown")
        assert violations == []


class TestRunFunction:
    def test_returns_correct_schema(self, tmp_path):
        with patch("ssa.checkers.check_prompt_injection.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["principle"] == _PRINCIPLE
        assert result["success"] is True
        assert "violations" in result
        assert "files_analyzed" in result
        assert "duration_ms" in result

    def test_empty_dir_no_violations(self, tmp_path):
        with patch("ssa.checkers.check_prompt_injection.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["violations"] == []

    def test_prompt_group_gets_the_pattern_pass(self, tmp_path):
        """The orchestrator hands `.prompt` templates over as their own "prompt" group."""
        f = _make_file(tmp_path, "system.prompt", "Answer the following: {user_input}\n")
        with patch("ssa.checkers.check_prompt_injection.check_server_available", return_value=False):
            result = run(tmp_path, "prompt", files=[f])
        assert result["files_analyzed"] == 1
        assert [v["file"] for v in result["violations"]] == ["system.prompt"]

    def test_prompt_group_never_reaches_the_ai(self, tmp_path):
        f = _make_file(tmp_path, "system.prompt", "Answer the following: {user_input}\n")
        with patch("ssa.checkers.check_prompt_injection.check_server_available", return_value=True), \
             patch("ssa.checkers.check_prompt_injection.analyze_files_parallel") as ai:
            run(tmp_path, "prompt", files=[f])
        ai.assert_not_called()

    def test_code_group_does_not_rescan_prompt_templates(self, tmp_path):
        """Templates used to be globbed on every run; once per language group would report them N times."""
        src = _make_file(tmp_path, "agent.py", "x = 1\n")
        _make_file(tmp_path, "system.prompt", "Answer the following: {user_input}\n")
        with patch("ssa.checkers.check_prompt_injection.check_server_available", return_value=False):
            result = run(tmp_path, "python", files=[src])
        assert result["violations"] == []
