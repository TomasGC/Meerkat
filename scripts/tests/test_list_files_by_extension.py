#!/usr/bin/env python3
"""Tests for list_files_by_extension.py"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from cli.list_files_by_extension import (
    DEFAULT_EXCLUDES,
    find_files_by_extension,
    is_excluded)
from common.utils import write_file_safe

@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure with various file types."""
    # Create directories
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "components").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "node_modules" / "package").mkdir(parents=True)
    (tmp_path / "bin").mkdir()
    (tmp_path / "obj").mkdir()
    (tmp_path / "dist").mkdir()

    # Create files
    files = [
        "README.md",
        "CHANGELOG.md",
        "src/main.py",
        "src/utils.py",
        "src/components/header.tsx",
        "src/components/footer.tsx",
        "tests/test_main.py",
        "tests/test_utils.py",
        "package.json",
        "tsconfig.json",
        "node_modules/package/index.js",  # Should be excluded
        "bin/executable",  # Should be excluded
        "obj/temp.obj",  # Should be excluded
        "dist/bundle.js",  # Should be excluded
    ]

    for file in files:
        file_path = tmp_path / file
        write_file_safe(file_path, f"Content of {file}")

    return tmp_path

def test_is_excluded_node_modules(tmp_path):
    """Test exclusion of node_modules files."""
    file_path = tmp_path / "node_modules" / "package" / "index.js"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_bin(tmp_path):
    """Test exclusion of bin directory."""
    file_path = tmp_path / "bin" / "executable"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_obj(tmp_path):
    """Test exclusion of obj directory."""
    file_path = tmp_path / "obj" / "temp.obj"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_dist(tmp_path):
    """Test exclusion of dist directory."""
    file_path = tmp_path / "dist" / "bundle.js"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_git(tmp_path):
    """Test exclusion of .git directory."""
    file_path = tmp_path / ".git" / "config"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_not_excluded_src(tmp_path):
    """Test that src files are NOT excluded."""
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert not is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_custom_pattern(tmp_path):
    """Test exclusion with custom patterns."""
    file_path = tmp_path / "temp" / "file.txt"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    custom_excludes = ["temp/"]
    assert is_excluded(file_path, tmp_path, custom_excludes)

def test_find_files_single_extension(sample_project):
    """Test finding files with single extension."""
    files = find_files_by_extension(sample_project, [".md"], DEFAULT_EXCLUDES)

    assert len(files) == 2
    file_names = [f.name for f in files]
    assert "README.md" in file_names
    assert "CHANGELOG.md" in file_names

def test_find_files_multiple_extensions(sample_project):
    """Test finding files with multiple extensions."""
    files = find_files_by_extension(sample_project, [".py", ".tsx"], DEFAULT_EXCLUDES)

    assert len(files) == 6  # 2 src .py, 2 tests .py, 2 .tsx
    file_names = [f.name for f in files]
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "header.tsx" in file_names
    assert "footer.tsx" in file_names

def test_find_files_normalizes_extensions(sample_project):
    """Test that extensions without dot are normalized."""
    # Test with "py" instead of ".py"
    files = find_files_by_extension(sample_project, ["py"], DEFAULT_EXCLUDES)

    assert len(files) == 4  # 2 src .py, 2 tests .py

def test_find_files_excludes_node_modules(sample_project):
    """Test that node_modules files are excluded."""
    files = find_files_by_extension(sample_project, [".js"], DEFAULT_EXCLUDES)

    # Should NOT find node_modules/package/index.js
    assert len(files) == 0

def test_find_files_excludes_dist(sample_project):
    """Test that dist files are excluded."""
    files = find_files_by_extension(sample_project, [".js"], DEFAULT_EXCLUDES)

    # Should NOT find dist/bundle.js
    assert len(files) == 0

def test_find_files_custom_exclude(sample_project):
    """Test with custom exclusion patterns."""
    files = find_files_by_extension(sample_project, [".py"], ["tests/"])

    # Should find src .py files but not tests .py files
    assert len(files) == 2
    file_names = [f.name for f in files]
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "test_main.py" not in file_names

def test_find_files_empty_result(sample_project):
    """Test when no files match."""
    files = find_files_by_extension(sample_project, [".nonexistent"], DEFAULT_EXCLUDES)

    assert files == []

def test_find_files_sorted(sample_project):
    """Test that results are sorted."""
    files = find_files_by_extension(sample_project, [".md"], DEFAULT_EXCLUDES)

    file_names = [f.name for f in files]
    assert file_names == sorted(file_names)

def test_find_files_deduplicates(tmp_path):
    """Test that duplicate files are removed."""
    # Create a file that matches multiple extensions
    file_path = tmp_path / "test.backup.txt"
    write_file_safe(file_path, "content")

    # Search for both .backup and .txt
    files = find_files_by_extension(tmp_path, [".backup", ".txt"], [])

    # Should only appear once
    assert len(files) == 1

def test_find_files_nonexistent_path():
    """Test error handling for nonexistent path."""
    nonexistent = Path("/nonexistent/path")

    # Should not raise error, just return empty list
    # (rglob on nonexistent path doesn't iterate)
    files = find_files_by_extension(nonexistent, [".txt"], DEFAULT_EXCLUDES)

    assert files == []

def test_default_excludes_comprehensive():
    """Test that DEFAULT_EXCLUDES has expected patterns."""
    expected_patterns = [
        "node_modules/",
        "vendor/",
        "bin/",
        "obj/",
        "dist/",
        "build/",
        ".git/",
        "__pycache__/",
        ".venv/",
        "venv/",
    ]

    for pattern in expected_patterns:
        assert pattern in DEFAULT_EXCLUDES

def test_find_files_case_sensitive_extension(sample_project):
    """Test that extension matching is case-sensitive."""
    # Create file with uppercase extension
    file_path = sample_project / "README.MD"
    write_file_safe(file_path, "content")

    # Search for lowercase .md
    files = find_files_by_extension(sample_project, [".md"], DEFAULT_EXCLUDES)

    # Should find .md but not .MD
    file_names = [f.name for f in files]
    assert "README.MD" not in file_names

def test_is_excluded_subdirectory(tmp_path):
    """Test exclusion of files in subdirectories of excluded paths."""
    file_path = tmp_path / "node_modules" / "package" / "lib" / "index.js"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    assert is_excluded(file_path, tmp_path, DEFAULT_EXCLUDES)

def test_is_excluded_relative_path_outside_root(tmp_path):
    """Test handling of paths outside root."""
    outside_path = Path("/some/other/path/file.txt")

    # Should return False (not throw exception)
    result = is_excluded(outside_path, tmp_path, DEFAULT_EXCLUDES)

    assert result == False

def test_find_files_preserves_full_path(sample_project):
    """Test that returned paths are full paths."""
    files = find_files_by_extension(sample_project, [".md"], DEFAULT_EXCLUDES)

    for file in files:
        assert file.is_absolute()
        assert str(sample_project) in str(file)
