#!/usr/bin/env python3
"""Tests for upload_coverage.py — unit tests"""

import json
from pathlib import Path

from upload_coverage import (
    discover_lcov_dir,
    load_manifest,
    upload_with_codecov,
)

def test_load_manifest_returns_path_dict(temp_dir):
    data = {"unit": "/tmp/cov/unit.lcov", "e2e": "/tmp/cov/e2e.lcov"}
    f = temp_dir / "manifest.json"
    f.write_text(json.dumps(data))
    result = load_manifest(f)
    assert result["unit"] == Path("/tmp/cov/unit.lcov")
    assert result["e2e"] == Path("/tmp/cov/e2e.lcov")

def test_load_manifest_empty(temp_dir):
    f = temp_dir / "manifest.json"
    f.write_text("{}")
    assert load_manifest(f) == {}

def test_discover_lcov_dir_flat_files(temp_dir):
    for tier in ("unit", "int_mock"):
        (temp_dir / f"coverage_{tier}.lcov").write_text("SF:x\nend_of_record\n")
    result = discover_lcov_dir(temp_dir)
    assert "unit" in result
    assert "int_mock" in result
    assert "int_real" not in result
    assert "e2e" not in result

def test_discover_lcov_dir_subdir_fallback(temp_dir):
    (temp_dir / "unit").mkdir()
    (temp_dir / "unit" / "lcov.info").write_text("SF:x\nend_of_record\n")
    result = discover_lcov_dir(temp_dir)
    assert "unit" in result

def test_discover_lcov_dir_empty_dir(temp_dir):
    result = discover_lcov_dir(temp_dir)
    assert result == {}

def test_discover_lcov_dir_prefers_flat_over_subdir(temp_dir):
    flat = temp_dir / "coverage_unit.lcov"
    flat.write_text("SF:flat.py\nend_of_record\n")
    (temp_dir / "unit").mkdir()
    (temp_dir / "unit" / "lcov.info").write_text("SF:subdir.py\nend_of_record\n")
    result = discover_lcov_dir(temp_dir)
    assert result["unit"] == flat

def test_upload_with_codecov_dry_run_returns_zero(temp_dir, minimal_lcov_file):
    rc = upload_with_codecov(
        lcov_file=minimal_lcov_file,
        flag="unit",
        repo=None, commit=None, branch=None, pr=None, token=None,
        dry_run=True, codecov_bin="codecov",
    )
    assert rc == 0

def test_upload_with_codecov_dry_run_includes_flag(capsys, temp_dir, minimal_lcov_file):
    upload_with_codecov(
        lcov_file=minimal_lcov_file,
        flag="int_mock",
        repo=None, commit=None, branch=None, pr=None, token=None,
        dry_run=True, codecov_bin="codecov",
    )
    captured = capsys.readouterr()
    assert "--flag" in captured.err
    assert "int_mock" in captured.err

def test_upload_token_not_logged_in_stderr(capsys, temp_dir, minimal_lcov_file):
    upload_with_codecov(
        lcov_file=minimal_lcov_file,
        flag="unit",
        repo=None, commit=None, branch=None, pr=None,
        token="super_secret_token_xyz",
        dry_run=True, codecov_bin="codecov",
    )
    captured = capsys.readouterr()
    assert "super_secret_token_xyz" not in captured.err
    assert "***" in captured.err

def test_upload_no_token_command_unchanged(capsys, temp_dir, minimal_lcov_file):
    upload_with_codecov(
        lcov_file=minimal_lcov_file,
        flag="unit",
        repo=None, commit=None, branch=None, pr=None,
        token=None,
        dry_run=True, codecov_bin="codecov",
    )
    captured = capsys.readouterr()
    assert "***" not in captured.err
