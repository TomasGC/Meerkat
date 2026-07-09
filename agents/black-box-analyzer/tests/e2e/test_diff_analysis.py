#!/usr/bin/env python3
"""Tests for diff_analysis.py — e2e tests (subprocess.run on script)"""

import json
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def _make_analysis(coverage: float, untested: int, critical: int = 0, high: int = 0,
                   by_endpoint: dict | None = None) -> dict:
    return {
        "coverage_summary": {
            "coverage_percent": coverage,
            "untested_scenarios": untested,
            "by_endpoint": by_endpoint or {},
        },
        "risk_summary": {
            "by_level": {"CRITICAL": critical, "HIGH": high},
        },
    }


def test_cli_missing_file_exits_one(temp_dir):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "diff_analysis.py"),
         str(temp_dir / "no.json"), str(temp_dir / "no2.json")],
        capture_output=True, text=True,
    )
    assert result.returncode == 1


def test_cli_json_format(temp_dir):
    b = temp_dir / "baseline.json"
    c = temp_dir / "current.json"
    b.write_text(json.dumps(_make_analysis(40.0, 5)))
    c.write_text(json.dumps(_make_analysis(60.0, 3)))
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "diff_analysis.py"),
         str(b), str(c), "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "coverage" in data
    assert data["coverage"]["trend"] == "improved"


def test_cli_regression_exits_one(temp_dir):
    b = temp_dir / "baseline.json"
    c = temp_dir / "current.json"
    b.write_text(json.dumps(_make_analysis(80.0, 2, by_endpoint={"/x": {"coverage_percent": 80.0}})))
    c.write_text(json.dumps(_make_analysis(60.0, 5, by_endpoint={"/x": {"coverage_percent": 20.0}})))
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "diff_analysis.py"), str(b), str(c)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1


def test_cli_no_regression_exits_zero(temp_dir):
    b = temp_dir / "baseline.json"
    c = temp_dir / "current.json"
    b.write_text(json.dumps(_make_analysis(40.0, 5)))
    c.write_text(json.dumps(_make_analysis(60.0, 3)))
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "diff_analysis.py"), str(b), str(c)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
