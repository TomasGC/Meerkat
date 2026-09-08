#!/usr/bin/env python3
"""Integration/mock tests for the 4 test gap checkers with realistic project layouts."""

from pathlib import Path
from unittest.mock import patch

from checkers.check_unit_gaps import run as run_unit
from checkers.check_integ_mock_gaps import run as run_integ_mock
from checkers.check_integ_real_gaps import run as run_integ_real
from checkers.check_e2e_gaps import run as run_e2e


def _make_project(root: Path) -> None:
    """Realistic Python project: 2 src files, 4 tiered test directories, utils.py uncovered in all tiers."""
    (root / "src").mkdir()
    (root / "src" / "service.py").write_text("def process(x): return x", encoding="utf-8")
    (root / "src" / "utils.py").write_text("def helper(): pass", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "unit").mkdir()
    (tests / "unit" / "test_service.py").write_text("def test_process(): pass", encoding="utf-8")
    integ = tests / "integration"
    integ.mkdir()
    (integ / "mock").mkdir()
    (integ / "mock" / "test_service_mock.py").write_text("def test_mock(): pass", encoding="utf-8")
    (integ / "real").mkdir()
    (integ / "real" / "test_service_real.py").write_text("def test_real(): pass", encoding="utf-8")
    (tests / "e2e").mkdir()
    (tests / "e2e" / "test_service_e2e.py").write_text("def test_e2e(): pass", encoding="utf-8")


def test_unit_gap_checker_discovers_uncovered_file(tmp_path):
    _make_project(tmp_path)
    with patch("checkers.check_unit_gaps.check_server_available", return_value=False):
        result = run_unit(tmp_path, "python")
    assert result["success"] is True
    assert result["files_analyzed"] == 2
    assert any("utils" in v["file"] for v in result["violations"])


def test_integ_mock_gap_checker_detects_gap(tmp_path):
    _make_project(tmp_path)
    with patch("checkers.check_integ_mock_gaps.check_server_available", return_value=False):
        result = run_integ_mock(tmp_path, "python")
    assert result["success"] is True
    assert any("utils" in v["file"] for v in result["violations"])


def test_integ_real_gap_checker_detects_gap(tmp_path):
    _make_project(tmp_path)
    with patch("checkers.check_integ_real_gaps.check_server_available", return_value=False):
        result = run_integ_real(tmp_path, "python")
    assert result["success"] is True
    assert any("utils" in v["file"] for v in result["violations"])


def test_e2e_gap_checker_detects_gap(tmp_path):
    _make_project(tmp_path)
    with patch("checkers.check_e2e_gaps.check_server_available", return_value=False):
        result = run_e2e(tmp_path, "python")
    assert result["success"] is True
    assert any("utils" in v["file"] for v in result["violations"])
