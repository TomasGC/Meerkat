#!/usr/bin/env python3
"""Tests for open_report.py — e2e tests (subprocess.run on script)"""

import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_main_skip_collect_no_files_returns_one(temp_dir):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "open_report.py"),
         str(temp_dir), "--skip-collect", "--no-browser"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "No lcov files found" in result.stderr


def test_main_skip_collect_with_existing_lcov_no_crash(temp_dir, minimal_lcov_file):
    cov_dir = temp_dir / ".coverage-tiers"
    cov_dir.mkdir()
    (cov_dir / "coverage_unit.lcov").write_text(minimal_lcov_file.read_text())
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "open_report.py"),
         str(temp_dir), "--skip-collect", "--no-browser", "--tiers", "unit"],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)
    assert "Traceback" not in result.stderr
