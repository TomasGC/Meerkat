#!/usr/bin/env python3
"""Tests for coverage_by_type.py — e2e tests (subprocess.run on script)"""

import json
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_main_json_output(sample_scenarios_json, sample_tests_json, temp_dir):
    out = temp_dir / "breakdown.json"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "coverage_by_type.py"),
         str(sample_scenarios_json), str(sample_tests_json),
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert "unit" in data
    assert "combined" in data


def test_main_markdown_output(sample_scenarios_json, sample_tests_json, temp_dir):
    md = temp_dir / "breakdown.md"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "coverage_by_type.py"),
         str(sample_scenarios_json), str(sample_tests_json),
         "--markdown", str(md)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert md.exists()
    assert "# Coverage by Test Type" in md.read_text()


def test_main_missing_scenarios_file_returns_one(temp_dir, sample_tests_json):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "coverage_by_type.py"),
         str(temp_dir / "no_such.json"), str(sample_tests_json)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_main_library_mode(sample_scenarios_json, sample_tests_json, temp_dir):
    out = temp_dir / "lib_breakdown.json"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "coverage_by_type.py"),
         str(sample_scenarios_json), str(sample_tests_json),
         "--mode", "library", "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert "combined" in data
