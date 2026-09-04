#!/usr/bin/env python3
"""Tests for open_report.py — int_real tests (real subprocess.run via _run helper)"""

from pathlib import Path

from open_report import _run

def test_run_prints_label_and_command(capsys, temp_dir):
    _run(["python", "-c", "pass"], temp_dir, "test-label")
    captured = capsys.readouterr()
    assert "[test-label]" in captured.err
    assert "python" in captured.err

def test_run_returns_zero_for_successful_command(temp_dir):
    rc = _run(["python", "-c", "pass"], temp_dir, "test")
    assert rc == 0

def test_run_returns_nonzero_for_failing_command(temp_dir):
    rc = _run(["python", "-c", "import sys; sys.exit(1)"], temp_dir, "test")
    assert rc == 1

def test_run_handles_path_objects_in_cmd(temp_dir):
    out_file = temp_dir / "marker.txt"
    rc = _run(
        ["python", "-c", f"open(r'{out_file}', 'w').close()"],
        temp_dir,
        "test",
    )
    assert rc == 0
