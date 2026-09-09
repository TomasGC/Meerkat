"""Unit tests for common/file_utils.py — discovery, language detection, git helpers."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common import file_utils
from common.file_utils import (
    detect_language,
    discover_files,
    get_branch_files,
    get_changed_files,
    get_staged_files,
    read_file_safe,
)


@pytest.fixture(autouse=True)
def _clear_discovery_cache():
    """discover_files memoizes by (path, extensions) and never invalidates."""
    file_utils._DISCOVERY_CACHE.clear()
    yield
    file_utils._DISCOVERY_CACHE.clear()


class TestDiscoverFiles:
    def test_finds_source_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.cs").write_text("class B {}\n")
        assert {f.name for f in discover_files(tmp_path)} == {"a.py", "b.cs"}

    def test_ignores_unknown_extensions(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hello\n")
        (tmp_path / "a.py").write_text("x = 1\n")
        assert [f.name for f in discover_files(tmp_path)] == ["a.py"]

    def test_extension_filter_narrows_results(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.go").write_text("package main\n")
        assert [f.name for f in discover_files(tmp_path, [".go"])] == ["b.go"]

    def test_skips_vendor_directories(self, tmp_path):
        vendored = tmp_path / "node_modules"
        vendored.mkdir()
        (vendored / "dep.js").write_text("module.exports = {}\n")
        (tmp_path / "app.js").write_text("console.log(1)\n")
        assert [f.name for f in discover_files(tmp_path)] == ["app.js"]

    def test_dockerfile_matched_without_extension(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM alpine\n")
        assert [f.name for f in discover_files(tmp_path)] == ["Dockerfile"]

    def test_dockerfile_excluded_when_extensions_given(self, tmp_path):
        """An explicit extension list means the caller wants suffixes only."""
        (tmp_path / "Dockerfile").write_text("FROM alpine\n")
        assert discover_files(tmp_path, [".py"]) == []

    def test_single_file_path_returns_that_file(self, tmp_path):
        target = tmp_path / "a.py"
        target.write_text("x = 1\n")
        assert discover_files(target) == [target]

    def test_single_file_path_with_wrong_suffix_returns_empty(self, tmp_path):
        target = tmp_path / "readme.txt"
        target.write_text("hi\n")
        assert discover_files(target) == []

    def test_nested_directories_are_searched(self, tmp_path):
        deep = tmp_path / "src" / "core"
        deep.mkdir(parents=True)
        (deep / "engine.py").write_text("x = 1\n")
        assert [f.name for f in discover_files(tmp_path)] == ["engine.py"]

    def test_results_are_sorted(self, tmp_path):
        for name in ("c.py", "a.py", "b.py"):
            (tmp_path / name).write_text("x = 1\n")
        assert [f.name for f in discover_files(tmp_path)] == ["a.py", "b.py", "c.py"]

    def test_result_is_cached_per_path_and_extensions(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        first = discover_files(tmp_path)
        (tmp_path / "b.py").write_text("y = 2\n")
        assert discover_files(tmp_path) == first, "cache must be reused within a process"
        file_utils._DISCOVERY_CACHE.clear()
        assert len(discover_files(tmp_path)) == 2

    def test_empty_directory_returns_empty(self, tmp_path):
        assert discover_files(tmp_path) == []


class TestDetectLanguage:
    def test_single_language_project(self, tmp_path):
        for name in ("a.py", "b.py", "c.py"):
            (tmp_path / name).write_text("x = 1\n")
        assert detect_language(tmp_path) == "python"

    def test_dominant_language_above_threshold(self, tmp_path):
        for name in ("a.py", "b.py", "c.py", "d.py"):
            (tmp_path / name).write_text("x = 1\n")
        (tmp_path / "e.go").write_text("package main\n")
        assert detect_language(tmp_path) == "python"

    def test_even_split_is_mixed(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.go").write_text("package main\n")
        assert detect_language(tmp_path) == "mixed"

    def test_no_source_files_is_unknown(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hello\n")
        assert detect_language(tmp_path) == "unknown"

    def test_dockerfile_only_is_unknown(self, tmp_path):
        """dockerfile has no extensions, so it never wins the extension count."""
        (tmp_path / "Dockerfile").write_text("FROM alpine\n")
        assert detect_language(tmp_path) == "unknown"


_GIT_HELPERS = [get_changed_files, get_branch_files, get_staged_files]


class TestGitHelpers:
    @pytest.mark.parametrize("helper", _GIT_HELPERS)
    def test_returns_none_when_git_fails(self, tmp_path, helper):
        completed = subprocess.CompletedProcess([], 128, "", "fatal")
        with patch("common.file_utils.subprocess.run", return_value=completed):
            assert helper(tmp_path) is None

    @pytest.mark.parametrize("helper", _GIT_HELPERS)
    def test_returns_none_when_git_raises(self, tmp_path, helper):
        with patch("common.file_utils.subprocess.run", side_effect=OSError("no git")):
            assert helper(tmp_path) is None

    @pytest.mark.parametrize("helper", _GIT_HELPERS)
    def test_resolves_names_against_the_repo_root(self, tmp_path, helper):
        (tmp_path / "a.py").write_text("x = 1\n")
        completed = subprocess.CompletedProcess([], 0, "a.py\n", "")
        with patch("common.file_utils.subprocess.run", return_value=completed):
            assert helper(tmp_path) == [tmp_path / "a.py"]

    @pytest.mark.parametrize("helper", _GIT_HELPERS)
    def test_drops_deleted_files(self, tmp_path, helper):
        """A rename or delete leaves a name git reports but that no longer exists."""
        completed = subprocess.CompletedProcess([], 0, "gone.py\n", "")
        with patch("common.file_utils.subprocess.run", return_value=completed):
            assert helper(tmp_path) == []

    @pytest.mark.parametrize("helper", _GIT_HELPERS)
    def test_blank_lines_ignored(self, tmp_path, helper):
        completed = subprocess.CompletedProcess([], 0, "\n  \n", "")
        with patch("common.file_utils.subprocess.run", return_value=completed):
            assert helper(tmp_path) == []

    def test_changed_files_passes_the_ref(self, tmp_path):
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch("common.file_utils.subprocess.run", return_value=completed) as run:
            get_changed_files(tmp_path, since="abc123")
        assert "abc123" in run.call_args[0][0]

    def test_branch_files_uses_three_dot_range(self, tmp_path):
        """Three dots diff since the merge base, so a moved main is not reported."""
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch("common.file_utils.subprocess.run", return_value=completed) as run:
            get_branch_files(tmp_path, base="develop")
        assert "develop...HEAD" in run.call_args[0][0]

    def test_staged_files_uses_cached_flag(self, tmp_path):
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch("common.file_utils.subprocess.run", return_value=completed) as run:
            get_staged_files(tmp_path)
        assert "--cached" in run.call_args[0][0]


class TestReadFileSafe:
    def test_reads_content(self, tmp_path):
        target = tmp_path / "a.py"
        target.write_text("x = 1\n")
        assert read_file_safe(target) == "x = 1\n"

    def test_missing_file_returns_empty_string(self, tmp_path):
        assert read_file_safe(tmp_path / "absent.py") == ""

    def test_truncates_beyond_max_chars(self, tmp_path):
        target = tmp_path / "big.py"
        target.write_text("a" * 100)
        result = read_file_safe(target, max_chars=10)
        assert result.startswith("a" * 10)
        assert "truncated" in result

    def test_content_at_limit_is_not_truncated(self, tmp_path):
        target = tmp_path / "exact.py"
        target.write_text("a" * 10)
        assert read_file_safe(target, max_chars=10) == "a" * 10

    def test_invalid_bytes_are_replaced_not_raised(self, tmp_path):
        target = tmp_path / "bin.py"
        target.write_bytes(b"x = \xff\xfe\n")
        assert read_file_safe(target).startswith("x = ")
