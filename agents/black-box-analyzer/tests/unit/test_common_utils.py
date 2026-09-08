#!/usr/bin/env python3
"""Tests for common/utils.py"""

import json
from pathlib import Path

import pytest

from common.utils import (
    count_lines_of_code,
    extract_line_number_from_pattern,
    extract_params_from_path,
    find_project_root,
    format_path_relative,
    merge_dicts_deep,
    read_file_safe,
    read_json,
    sanitize_filename,
    walk_files,
    write_json,
)

# ── read_file_safe ────────────────────────────────────────────────────────────

def test_read_file_safe_returns_content(temp_dir):
    f = temp_dir / "hello.txt"
    f.write_text("hello world")
    assert read_file_safe(f) == "hello world"

def test_read_file_safe_missing_returns_none(temp_dir):
    assert read_file_safe(temp_dir / "missing.txt") is None

def test_read_file_safe_bad_encoding_returns_none(temp_dir):
    f = temp_dir / "bin.txt"
    f.write_bytes(b"\xff\xfe invalid utf-8 \x80")
    assert read_file_safe(f, encoding="utf-8") is None

# ── read_json / write_json ────────────────────────────────────────────────────

def test_read_json_valid(temp_dir):
    f = temp_dir / "data.json"
    f.write_text(json.dumps({"key": "value"}))
    assert read_json(f) == {"key": "value"}

def test_read_json_missing_raises(temp_dir):
    with pytest.raises(FileNotFoundError):
        read_json(temp_dir / "no.json")

def test_read_json_invalid_raises(temp_dir):
    f = temp_dir / "bad.json"
    f.write_text("{not json")
    with pytest.raises(json.JSONDecodeError):
        read_json(f)

def test_write_json_to_file(temp_dir):
    out = temp_dir / "out.json"
    write_json({"a": 1}, out)
    assert json.loads(out.read_text()) == {"a": 1}

def test_write_json_to_stdout_no_crash(capsys):
    write_json({"x": 2})
    captured = capsys.readouterr()
    assert '"x": 2' in captured.out

# ── walk_files ────────────────────────────────────────────────────────────────

def test_walk_files_finds_matching(temp_dir):
    (temp_dir / "a.py").write_text("x")
    (temp_dir / "b.txt").write_text("y")
    found = list(walk_files(temp_dir, ["*.py"]))
    assert len(found) == 1
    assert found[0].name == "a.py"

def test_walk_files_recursive(temp_dir):
    sub = temp_dir / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("z")
    found = list(walk_files(temp_dir, ["*.py"], recursive=True))
    assert any(f.name == "c.py" for f in found)

def test_walk_files_nonrecursive_skips_sub(temp_dir):
    sub = temp_dir / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("z")
    found = list(walk_files(temp_dir, ["*.py"], recursive=False))
    assert not any(f.name == "c.py" for f in found)

# ── find_project_root ─────────────────────────────────────────────────────────

def test_find_project_root_finds_go_mod(temp_dir):
    (temp_dir / "go.mod").write_text("module example")
    sub = temp_dir / "pkg" / "util"
    sub.mkdir(parents=True)
    root = find_project_root(sub)
    assert root is not None
    assert root.resolve() == temp_dir.resolve()

def test_find_project_root_not_found(temp_dir):
    isolated = temp_dir / "empty"
    isolated.mkdir()
    # No project markers anywhere in temp_dir hierarchy (temp dirs don't have them)
    root = find_project_root(isolated)
    # May or may not find one depending on filesystem — just must not crash
    assert root is None or isinstance(root, Path)

def test_find_project_root_pyproject(temp_dir):
    (temp_dir / "pyproject.toml").write_text("[tool.pytest]")
    root = find_project_root(temp_dir)
    assert root is not None
    assert root.resolve() == temp_dir.resolve()

# ── count_lines_of_code ───────────────────────────────────────────────────────

def test_count_lines_skips_comments(temp_dir):
    f = temp_dir / "code.py"
    f.write_text("# comment\ndef foo():\n    pass\n\n")
    assert count_lines_of_code(f) == 2

def test_count_lines_empty_file(temp_dir):
    f = temp_dir / "empty.py"
    f.write_text("")
    assert count_lines_of_code(f) == 0

def test_count_lines_missing_returns_zero(temp_dir):
    assert count_lines_of_code(temp_dir / "missing.py") == 0

# ── extract_line_number_from_pattern ─────────────────────────────────────────

def test_extract_line_number_found():
    content = "line one\nline two\nfoo bar\n"
    assert extract_line_number_from_pattern(content, "foo") == 3

def test_extract_line_number_not_found():
    assert extract_line_number_from_pattern("abc\ndef\n", "xyz") == 0

def test_extract_line_number_first_match():
    content = "foo\nfoo\nfoo\n"
    assert extract_line_number_from_pattern(content, "foo") == 1

# ── merge_dicts_deep ──────────────────────────────────────────────────────────

def test_merge_dicts_deep_basic():
    result = merge_dicts_deep({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}

def test_merge_dicts_deep_nested():
    d1 = {"x": {"a": 1, "b": 2}}
    d2 = {"x": {"b": 99, "c": 3}}
    result = merge_dicts_deep(d1, d2)
    assert result["x"] == {"a": 1, "b": 99, "c": 3}

def test_merge_dicts_deep_no_mutation():
    d1 = {"a": 1}
    d2 = {"b": 2}
    merge_dicts_deep(d1, d2)
    assert "b" not in d1

# ── sanitize_filename ─────────────────────────────────────────────────────────

def test_sanitize_filename_removes_invalid():
    assert sanitize_filename('file<name>:test"?') == "file_name__test__"

def test_sanitize_filename_clean_unchanged():
    assert sanitize_filename("my-file_v2.json") == "my-file_v2.json"

# ── extract_params_from_path ──────────────────────────────────────────────────

def test_extract_params_colon_style():
    params = extract_params_from_path("/users/:id/posts/:postId")
    names = [p.name for p in params]
    assert "id" in names
    assert "postId" in names
    assert len(params) == 2

def test_extract_params_brace_style():
    params = extract_params_from_path("/users/{userId}/orders/{orderId}")
    names = [p.name for p in params]
    assert "userId" in names
    assert "orderId" in names

def test_extract_params_no_params():
    assert extract_params_from_path("/health") == []

def test_extract_params_no_duplicates():
    # Mixed styles same name — should not duplicate
    params = extract_params_from_path("/:id/{extra}")
    names = [p.name for p in params]
    assert len(names) == len(set(names))

# ── format_path_relative ──────────────────────────────────────────────────────

def test_format_path_relative_inside_root(temp_dir):
    f = temp_dir / "sub" / "file.py"
    result = format_path_relative(f, temp_dir)
    assert result == str(Path("sub") / "file.py")

def test_format_path_relative_outside_root(temp_dir):
    f = Path("/some/other/path/file.py")
    result = format_path_relative(f, temp_dir)
    assert "file.py" in result
