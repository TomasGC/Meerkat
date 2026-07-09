#!/usr/bin/env python3
"""Tests for parallel_analyzer.py — e2e tests (subprocess.run on script)"""

import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "parallel_analyzer.py"), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_cli_nonexistent_path_returns_one():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "parallel_analyzer.py"),
         "/nonexistent/xyz_path_abc"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
