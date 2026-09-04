"""Tests for file_utils — discovery, language detection, git incremental helpers."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import (
    _DISCOVERY_CACHE,
    detect_language,
    discover_files,
    get_changed_files,
    get_staged_files,
)


@pytest.fixture(autouse=True)
def clear_discovery_cache():
    _DISCOVERY_CACHE.clear()
    yield
    _DISCOVERY_CACHE.clear()


class TestDiscoverFiles:
    def test_single_file(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("x = 1")
        result = discover_files(f, [".py"])
        assert result == [f]

    def test_skips_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.py").write_text("x")
        (tmp_path / "app.py").write_text("x")
        result = discover_files(tmp_path, [".py"])
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_skips_pycache(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("x")
        (tmp_path / "real.py").write_text("x")
        result = discover_files(tmp_path, [".py"])
        assert len(result) == 1

    def test_skips_bin_obj_dist(self, tmp_path):
        for skip_dir in ("bin", "obj", "dist"):
            d = tmp_path / skip_dir
            d.mkdir(exist_ok=True)
            (d / "file.cs").write_text("x")
        (tmp_path / "Program.cs").write_text("x")
        result = discover_files(tmp_path, [".cs"])
        assert len(result) == 1

    def test_caches_results(self, tmp_path):
        (tmp_path / "a.py").write_text("x")
        r1 = discover_files(tmp_path, [".py"])
        r2 = discover_files(tmp_path, [".py"])
        assert r1 is r2  # same list object from cache

    def test_extension_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "b.ts").write_text("x")
        py_only = discover_files(tmp_path, [".py"])
        assert all(f.suffix == ".py" for f in py_only)


class TestDetectLanguage:
    def test_python_dominant(self, tmp_path):
        for i in range(5):
            (tmp_path / f"f{i}.py").write_text("x")
        (tmp_path / "one.ts").write_text("x")
        assert detect_language(tmp_path) == "python"

    def test_mixed_when_no_dominant(self, tmp_path):
        for i in range(3):
            (tmp_path / f"a{i}.py").write_text("x")
        for i in range(3):
            (tmp_path / f"b{i}.ts").write_text("x")
        assert detect_language(tmp_path) == "mixed"

    def test_unknown_when_no_source(self, tmp_path):
        (tmp_path / "README.md").write_text("hello")
        assert detect_language(tmp_path) == "unknown"


class TestGitHelpers:
    def test_get_changed_files_returns_existing(self, tmp_path):
        f = tmp_path / "changed.py"
        f.write_text("x")
        mock_result = MagicMock(returncode=0, stdout="changed.py\n")
        with patch("subprocess.run", return_value=mock_result):
            result = get_changed_files(tmp_path, since="HEAD~1")
        assert result == [f]

    def test_get_changed_files_returns_none_on_failure(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            result = get_changed_files(tmp_path)
        assert result is None

    def test_get_changed_files_returns_none_on_exception(self, tmp_path):
        with patch("subprocess.run", side_effect=Exception("no git")):
            result = get_changed_files(tmp_path)
        assert result is None

    def test_get_staged_files_filters_nonexistent(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="nonexistent.py\n")
        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files(tmp_path)
        assert result == []

    def test_get_staged_files_returns_none_on_failure(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files(tmp_path)
        assert result is None
