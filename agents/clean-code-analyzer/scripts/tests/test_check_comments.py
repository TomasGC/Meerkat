"""Tests for check_comments — TODO/FIXME, commented-out code."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from checkers.check_comments import _check_file


class TestTodoFixme:
    def test_detects_todo(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# TODO: fix this later\nx = 1\n")
        violations = _check_file(f, tmp_path)
        todo_violations = [v for v in violations if "TODO" in v["message"]]
        assert len(todo_violations) == 1

    def test_detects_fixme(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# FIXME: broken\n")
        violations = _check_file(f, tmp_path)
        assert any("FIXME" in v["message"] for v in violations)

    def test_detects_hack(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# HACK: workaround for bug\n")
        violations = _check_file(f, tmp_path)
        assert any("HACK" in v["message"] for v in violations)

    def test_case_insensitive(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# todo: do something\n")
        violations = _check_file(f, tmp_path)
        assert len(violations) >= 1

    def test_no_false_positive_on_normal_comment(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# This function processes orders\nx = 1\n")
        violations = _check_file(f, tmp_path)
        todo = [v for v in violations if v["message"].startswith(("TODO", "FIXME", "HACK", "XXX"))]
        assert len(todo) == 0


class TestCommentedOutCode:
    def test_detects_consecutive_commented_code(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x = 1\n# def old_func():\n#     return x\n")
        violations = _check_file(f, tmp_path)
        code_violations = [v for v in violations if "Commented-out" in v["message"]]
        assert len(code_violations) >= 1

    def test_no_violation_for_single_commented_line(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# def old_func():\nx = 1\n")
        violations = _check_file(f, tmp_path)
        code_violations = [v for v in violations if "Commented-out" in v["message"]]
        assert len(code_violations) == 0


class TestRunSignature:
    def test_accepts_files_param(self, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1\n")
        from checkers.check_comments import run
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
