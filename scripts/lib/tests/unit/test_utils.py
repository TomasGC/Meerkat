#!/usr/bin/env python3
"""Tests for lib/utils.py — run_command (subprocess mocked) and write_file_safe."""

import subprocess
from unittest.mock import MagicMock, patch

from lib.utils import run_command, write_file_safe


def test_run_command_returns_code_and_streams():
    completed = MagicMock(returncode=3, stdout="out", stderr="err")
    with patch("lib.utils.subprocess.run", return_value=completed) as run:
        assert run_command(["git", "status"], timeout=7) == (3, "out", "err")
    assert run.call_args.kwargs["timeout"] == 7
    assert run.call_args.kwargs["check"] is False


def test_run_command_reports_timeout():
    with patch("lib.utils.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
        assert run_command(["git"], timeout=2) == (-1, "", "Command timed out after 2s")


def test_run_command_reports_missing_binary():
    with patch("lib.utils.subprocess.run", side_effect=FileNotFoundError("no such tool")):
        code, out, err = run_command(["nope"])
    assert (code, out) == (-1, "")
    assert "no such tool" in err


def test_write_file_safe_creates_parent_directories(tmp_path):
    target = tmp_path / "a" / "b" / "c.txt"
    assert write_file_safe(target, "héllo") is True
    assert target.read_text(encoding="utf-8") == "héllo"


def test_write_file_safe_returns_false_when_target_is_a_directory(tmp_path):
    assert write_file_safe(tmp_path, "x") is False
