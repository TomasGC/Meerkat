"""Tests for checkers/_utils.py"""

from pathlib import Path

import pytest

from checkers._utils import (
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
