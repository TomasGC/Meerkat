#!/usr/bin/env python3
"""Tests for open_report.py — int_mock tests (shutil.which patched)"""

from pathlib import Path
from unittest.mock import patch

from open_report import step_merge, step_reportgenerator

def test_step_merge_fallback_concatenates(temp_dir, minimal_lcov_file):
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = step_merge([minimal_lcov_file], output)
    assert ok is True
    assert output.exists()
    assert "SF:" in output.read_text()

def test_step_merge_output_contains_all_sources(temp_dir):
    a = temp_dir / "a.lcov"
    b = temp_dir / "b.lcov"
    a.write_text("SF:src/a.py\nDA:1,1\nend_of_record\n")
    b.write_text("SF:src/b.py\nDA:2,1\nend_of_record\n")
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        step_merge([a, b], out)
    content = out.read_text()
    assert "src/a.py" in content
    assert "src/b.py" in content

def test_step_merge_skips_nonexistent_files(temp_dir, minimal_lcov_file):
    ghost = temp_dir / "ghost.lcov"
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = step_merge([minimal_lcov_file, ghost], out)
    assert ok is True

def test_step_reportgenerator_not_found_returns_false(temp_dir):
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            ok = step_reportgenerator("*.lcov", temp_dir / "report", "test")
    assert ok is False

def test_step_reportgenerator_warns_when_missing(temp_dir, capsys):
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            step_reportgenerator("*.lcov", temp_dir / "report", "test")
    captured = capsys.readouterr()
    assert "ReportGenerator not found" in captured.err

def test_step_reportgenerator_success_returns_true(temp_dir):
    with patch("shutil.which", return_value="/usr/bin/reportgenerator"), \
         patch("open_report._run", return_value=0):
        ok = step_reportgenerator("*.lcov", temp_dir / "report", "test")
    assert ok is True
