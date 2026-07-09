#!/usr/bin/env python3
"""Tests for generate_ci_workflow.py — e2e tests (subprocess.run on script)"""

import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_main_dry_run_python_project(minimal_project_info_json):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "generate_ci_workflow.py"),
         str(minimal_project_info_json), "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "jobs:" in result.stdout
    assert "unit" in result.stdout


def test_main_output_file_written(minimal_project_info_json, temp_dir):
    out = temp_dir / "coverage.yml"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "generate_ci_workflow.py"),
         str(minimal_project_info_json), "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert out.exists()
    assert "jobs:" in out.read_text()


def test_main_directory_auto_detects_project_info(minimal_project_info_json, temp_dir):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "generate_ci_workflow.py"),
         str(temp_dir), "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_main_nonexistent_json_errors(temp_dir):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "generate_ci_workflow.py"),
         str(temp_dir / "nonexistent.json"), "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
