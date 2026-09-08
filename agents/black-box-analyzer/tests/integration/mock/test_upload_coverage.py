#!/usr/bin/env python3
"""Tests for upload_coverage.py — int_mock tests (shutil.which patched)"""

from pathlib import Path
from unittest.mock import patch

from upload_coverage import _find_codecov, _merge_lcov

def test_find_codecov_returns_none_when_absent():
    with patch("shutil.which", return_value=None):
        assert _find_codecov() is None

def test_find_codecov_returns_path_when_present():
    with patch("shutil.which", side_effect=lambda name: "/usr/bin/codecov" if name == "codecov" else None):
        assert _find_codecov() == "/usr/bin/codecov"

def test_merge_lcov_fallback_concatenates(temp_dir, minimal_lcov_file):
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([minimal_lcov_file], output)
    assert ok is True
    assert output.exists()
    assert "SF:" in output.read_text()

def test_merge_lcov_skips_nonexistent_files(temp_dir):
    output = temp_dir / "combined.lcov"
    ghost = temp_dir / "ghost.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([ghost], output)
    assert ok is True
    content = output.read_text(encoding="utf-8")
    assert "SF:" not in content

def test_merge_lcov_multiple_files(temp_dir, minimal_lcov_file):
    second = temp_dir / "coverage_int.lcov"
    second.write_text("SF:src/other.py\nDA:5,2\nend_of_record\n")
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = _merge_lcov([minimal_lcov_file, second], output)
    assert ok
    content = output.read_text()
    assert "src/main.py" in content
    assert "src/other.py" in content
