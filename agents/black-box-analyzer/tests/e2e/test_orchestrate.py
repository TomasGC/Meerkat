#!/usr/bin/env python3
"""Tests for orchestrate.py — e2e tests (subprocess.run on script)"""

import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_clear_cache_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--clear-cache"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Cleared" in result.stdout


def test_gaps_help_shows_the_engine_cli():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--gaps", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--checks" in result.stdout and "--min-severity" in result.stdout


def test_gaps_clear_cache_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--gaps", "--clear-cache"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Cleared" in result.stderr


def test_gaps_nonexistent_path_exits_nonzero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--gaps",
         "--path", "/nonexistent/xyz_path_abc_orchestrate_test"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_nonexistent_path_exits_nonzero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"),
         "--path", "/nonexistent/xyz_path_abc_orchestrate_test"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
