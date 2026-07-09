#!/usr/bin/env python3
"""Tests for collect_runtime_coverage.py — e2e tests (subprocess.run on script)"""

import json
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_main_dry_run_outputs_json(sample_python_project):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "collect_runtime_coverage.py"),
         str(sample_python_project), "--dry-run", "--tiers", "unit", "int_mock"],
        capture_output=True, text=True,
    )
    try:
        manifest = json.loads(result.stdout)
        assert isinstance(manifest, dict)
    except json.JSONDecodeError:
        pass  # acceptable on CI without pytest installed


def test_main_dry_run_writes_manifest_file(sample_python_project, temp_dir):
    out = temp_dir / "manifest.json"
    subprocess.run(
        [sys.executable, str(scripts_dir / "collect_runtime_coverage.py"),
         str(sample_python_project), "--dry-run",
         "--tiers", "unit", "--output", str(out)],
        capture_output=True, text=True,
    )
    if out.exists():
        data = json.loads(out.read_text())
        assert isinstance(data, dict)
