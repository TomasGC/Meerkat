#!/usr/bin/env python3
"""Tests for open_report.py — unit tests (print_summary, step_merge no-files)"""

import json
from pathlib import Path

from open_report import print_summary, step_merge

def test_step_merge_no_files_returns_false(temp_dir):
    ok = step_merge([], temp_dir / "out.lcov")
    assert ok is False

def test_print_summary_no_file_is_noop(temp_dir):
    print_summary(temp_dir, [], temp_dir / "combined.lcov")

def test_print_summary_with_valid_file(temp_dir, capsys):
    data = {
        "summary": {
            "linecoverage": 78.5,
            "branchcoverage": 65.0,
            "coverablelines": 200,
            "coveredlines": 157,
            "assemblies": [{"classes": ["A", "B", "C"]}],
        }
    }
    (temp_dir / "Summary.json").write_text(json.dumps(data))
    print_summary(temp_dir, [], temp_dir / "combined.lcov")
    captured = capsys.readouterr()
    assert "78.5" in captured.err
    assert "65.0" in captured.err

def test_print_summary_counts_classes_across_assemblies(temp_dir, capsys):
    data = {
        "summary": {
            "linecoverage": 50.0,
            "branchcoverage": 40.0,
            "coverablelines": 100,
            "coveredlines": 50,
            "assemblies": [
                {"classes": ["A", "B"]},
                {"classes": ["C", "D", "E"]},
            ],
        }
    }
    (temp_dir / "Summary.json").write_text(json.dumps(data))
    print_summary(temp_dir, [], temp_dir / "combined.lcov")
    captured = capsys.readouterr()
    assert "5" in captured.err

def test_print_summary_handles_corrupt_json(temp_dir):
    (temp_dir / "Summary.json").write_text("not-json")
    print_summary(temp_dir, [], temp_dir / "combined.lcov")

def test_print_summary_missing_assemblies_key(temp_dir, capsys):
    data = {
        "summary": {
            "linecoverage": 50.0,
            "branchcoverage": 30.0,
            "coverablelines": 100,
            "coveredlines": 50,
        }
    }
    (temp_dir / "Summary.json").write_text(__import__("json").dumps(data))
    print_summary(temp_dir, [], temp_dir / "combined.lcov")
