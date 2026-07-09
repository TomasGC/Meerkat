#!/usr/bin/env python3
"""Tests for upload_coverage.py — e2e tests (subprocess.run on script)"""

import json
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_main_dry_run_from_manifest(temp_dir, minimal_lcov_file):
    manifest = {"unit": str(minimal_lcov_file)}
    mf = temp_dir / "manifest.json"
    mf.write_text(json.dumps(manifest))
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "upload_coverage.py"),
         str(mf), "--dry-run", "--tiers", "unit"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "uploaded" in out
    assert "unit" in out["uploaded"]


def test_main_no_manifest_no_dir_errors():
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "upload_coverage.py")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_main_lcov_dir_dry_run(temp_dir):
    for tier in ("unit", "e2e"):
        (temp_dir / f"coverage_{tier}.lcov").write_text("SF:x\nend_of_record\n")
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "upload_coverage.py"),
         "--lcov-dir", str(temp_dir), "--dry-run", "--tiers", "unit", "e2e"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "unit" in out["uploaded"]
    assert "e2e" in out["uploaded"]
