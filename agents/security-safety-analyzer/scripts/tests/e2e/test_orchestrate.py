"""E2E tests for orchestrate.py — subprocess execution."""
import subprocess
import sys
from pathlib import Path

import pytest

scripts_dir = Path(__file__).parent.parent.parent


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Security Safety Analyzer" in result.stdout or "usage" in result.stdout.lower()


def test_clear_cache_exits_zero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"), "--clear-cache"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "Cleared" in combined or "cache" in combined.lower()


def test_nonexistent_path_exits_nonzero():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "orchestrate.py"),
         "--path", "/nonexistent/xyz_path_abc_ssa_test"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
