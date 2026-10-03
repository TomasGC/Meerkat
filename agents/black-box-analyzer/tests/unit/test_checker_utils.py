"""Tests for checkers/_utils.py"""

from pathlib import Path

import pytest

from bba.checkers._utils import (
    find_source_files,
    find_tier_test_files,
    has_test_in_tier,
    is_test_file,
)


# --- is_test_file ---

def test_is_test_file_test_prefix():
    assert is_test_file(Path("tests/unit/test_foo.py")) is True


def test_is_test_file_test_suffix():
    assert is_test_file(Path("src/foo_test.go")) is True


def test_is_test_file_spec_suffix():
    assert is_test_file(Path("src/foo.spec.ts")) is True


def test_is_test_file_mock_prefix():
    assert is_test_file(Path("src/mock_db.py")) is True


def test_is_test_file_regular_source():
    assert is_test_file(Path("src/user_service.py")) is False


def test_is_test_file_regular_go():
    assert is_test_file(Path("handlers/users.go")) is False


# --- has_test_in_tier ---

def test_has_test_in_tier_python_match():
    tests = [Path("tests/unit/test_foo.py")]
    assert has_test_in_tier(Path("src/foo.py"), tests) is True


def test_has_test_in_tier_go_match():
    tests = [Path("handlers/users_test.go")]
    assert has_test_in_tier(Path("handlers/users.go"), tests) is True


def test_has_test_in_tier_no_match():
    tests = [Path("tests/unit/test_bar.py")]
    assert has_test_in_tier(Path("src/foo.py"), tests) is False


def test_has_test_in_tier_empty_list():
    assert has_test_in_tier(Path("src/foo.py"), []) is False


def test_has_test_in_tier_partial_stem_match():
    # "foo" is in "test_foobar" — intentional: broad matching avoids false negatives
    tests = [Path("tests/unit/test_foobar.py")]
    assert has_test_in_tier(Path("src/foo.py"), tests) is True


# --- find_source_files ---

def test_find_source_files_excludes_test_files(tmp_path):
    (tmp_path / "service.py").write_text("pass", encoding="utf-8")
    (tmp_path / "test_service.py").write_text("pass", encoding="utf-8")
    result = find_source_files(tmp_path, "python")
    names = [f.name for f in result]
    assert "service.py" in names
    assert "test_service.py" not in names


def test_find_source_files_filters_by_language(tmp_path):
    (tmp_path / "app.py").write_text("pass", encoding="utf-8")
    (tmp_path / "app.ts").write_text("export {}", encoding="utf-8")
    result = find_source_files(tmp_path, "python")
    assert all(f.suffix == ".py" for f in result)


def test_find_source_files_with_files_filter(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("pass", encoding="utf-8")
    b.write_text("pass", encoding="utf-8")
    result = find_source_files(tmp_path, "python", files=[a])
    assert result == [a]


def test_find_source_files_files_filter_excludes_tests(tmp_path):
    src = tmp_path / "svc.py"
    tst = tmp_path / "test_svc.py"
    src.write_text("pass", encoding="utf-8")
    tst.write_text("pass", encoding="utf-8")
    result = find_source_files(tmp_path, "python", files=[src, tst])
    assert result == [src]


# --- find_tier_test_files ---

def test_find_tier_test_files_unit(tmp_path):
    unit_dir = tmp_path / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    f = unit_dir / "test_foo.py"
    f.write_text("pass", encoding="utf-8")
    result = find_tier_test_files(tmp_path, ["unit"])
    assert f in result


def test_find_tier_test_files_integration_mock(tmp_path):
    mock_dir = tmp_path / "tests" / "integration" / "mock"
    mock_dir.mkdir(parents=True)
    f = mock_dir / "test_foo_mock.py"
    f.write_text("pass", encoding="utf-8")
    result = find_tier_test_files(tmp_path, ["integration", "mock"])
    assert f in result


def test_find_tier_test_files_does_not_cross_tiers(tmp_path):
    unit_dir = tmp_path / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    (unit_dir / "test_foo.py").write_text("pass", encoding="utf-8")
    result = find_tier_test_files(tmp_path, ["integration", "mock"])
    assert result == []


def test_find_tier_test_files_empty_when_no_dirs(tmp_path):
    result = find_tier_test_files(tmp_path, ["unit"])
    assert result == []


# --- run_gap_checker (engine port, #20) ---

from unittest.mock import patch

import bba.checkers._utils as utils_mod
from bba.checkers._utils import run_gap_checker


def _gap(tmp_path, **kwargs):
    return run_gap_checker(
        tmp_path, "python", tier=["unit"], principle="UNIT_GAP", prompt="unit_gaps",
        missing_message="No unit test file found for this source file",
        ai_message=lambda item: f"Missing unit test [{item.get('function')}]", **kwargs,
    )


def _project_with_one_tested_file(tmp_path):
    (tmp_path / "billing.py").write_text("def a(): pass", encoding="utf-8")
    (tmp_path / "orders.py").write_text("def b(): pass", encoding="utf-8")
    unit = tmp_path / "tests" / "unit"
    unit.mkdir(parents=True)
    (unit / "test_billing.py").write_text("def test_billing(): pass", encoding="utf-8")


def test_gap_ai_only_sees_files_without_a_tier_test(tmp_path):
    """The prompt cannot see tests, so a file that has some is never sent to it."""
    _project_with_one_tested_file(tmp_path)
    with patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", return_value=[]) as ai:
        _gap(tmp_path)
    assert [f.name for f in ai.call_args.args[0]] == ["orders.py"]


def test_gap_mechanical_finding_reaches_the_prompt(tmp_path):
    _project_with_one_tested_file(tmp_path)
    with patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", return_value=[]) as ai:
        _gap(tmp_path)
    slots = ai.call_args.kwargs["extra_slots"]
    assert [s["known_findings"] for s in slots.values()] == ["- whole file: No unit test file found for this source file"]


def test_gap_mechanical_finding_kept_when_server_is_up(tmp_path):
    """Before #20 the server being up replaced the mechanical layer instead of adding to it."""
    _project_with_one_tested_file(tmp_path)
    with patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", return_value=[]):
        result = _gap(tmp_path)
    assert [(v["file"], v["line"]) for v in result["violations"]] == [("orders.py", 0)]


def test_gap_ai_finding_on_first_lines_survives_reconciliation(tmp_path):
    """A whole-file finding must not proximity-drop a function defined on line 1."""
    _project_with_one_tested_file(tmp_path)
    item = {"source_file": str(tmp_path / "orders.py"), "function": "b", "line": 1, "severity": "high"}
    with patch("lib.engine.hybrid.check_server_available", return_value=True), \
         patch("lib.engine.hybrid.analyze_files_parallel", return_value=[item]):
        result = _gap(tmp_path)
    assert sorted(v["line"] for v in result["violations"]) == [0, 1]


def test_gap_no_server_still_reports_mechanical(tmp_path):
    _project_with_one_tested_file(tmp_path)
    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = _gap(tmp_path)
    assert result["files_analyzed"] == 2
    assert [v["message"] for v in result["violations"]] == ["No unit test file found for this source file"]


def test_utils_keeps_no_language_table():
    """Languages and skip dirs come from the shared config through lib.engine.discovery."""
    assert not hasattr(utils_mod, "_LANG_EXTENSIONS")
    assert not hasattr(utils_mod, "EXCLUDED_DIRS")


def test_find_source_files_skips_migrations(tmp_path):
    (tmp_path / "0001_initial_migration.py").write_text("pass", encoding="utf-8")
    (tmp_path / "models.py").write_text("pass", encoding="utf-8")
    assert [f.name for f in find_source_files(tmp_path, "python")] == ["models.py"]
