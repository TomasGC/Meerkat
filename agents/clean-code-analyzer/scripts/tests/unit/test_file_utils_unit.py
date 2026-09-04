"""Unit tests for common/file_utils.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common.file_utils as fu
from common.file_utils import get_changed_files, get_staged_files, detect_language, read_file_safe


@pytest.fixture(autouse=True)
def clear_discovery_cache():
    """Reset the in-process discovery cache between tests."""
    fu._DISCOVERY_CACHE.clear()
    yield
    fu._DISCOVERY_CACHE.clear()


# ── discover_files ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_discover_files_finds_py(tmp_path):
    """discover_files() returns .py files under path."""
    (tmp_path / "a.py").write_text("pass")
    (tmp_path / "b.py").write_text("pass")
    result = fu.discover_files(tmp_path, [".py"])
    names = {f.name for f in result}
    assert "a.py" in names
    assert "b.py" in names


@pytest.mark.unit
@pytest.mark.parametrize("skip_dir", ["__pycache__", "node_modules", ".git", "dist"])
def test_discover_files_skips_directories(tmp_path, skip_dir):
    """discover_files() skips files inside known skip directories."""
    skip = tmp_path / skip_dir
    skip.mkdir()
    (skip / "hidden.py").write_text("pass")
    (tmp_path / "visible.py").write_text("pass")

    result = fu.discover_files(tmp_path, [".py"])
    names = {f.name for f in result}
    assert "hidden.py" not in names
    assert "visible.py" in names


# ── detect_language ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_detect_language_python(tmp_path):
    """Majority .py files → 'python'."""
    for i in range(5):
        (tmp_path / f"mod{i}.py").write_text("pass")
    assert fu.detect_language(tmp_path) == "python"


@pytest.mark.unit
def test_detect_language_typescript(tmp_path):
    """Majority .ts files → 'typescript'."""
    for i in range(5):
        (tmp_path / f"mod{i}.ts").write_text("export {};")
    assert fu.detect_language(tmp_path) == "typescript"


@pytest.mark.unit
def test_detect_language_mixed(tmp_path):
    """Even split → 'mixed' (no language > 60%)."""
    for i in range(3):
        (tmp_path / f"py{i}.py").write_text("pass")
    for i in range(3):
        (tmp_path / f"ts{i}.ts").write_text("export {};")
    result = fu.detect_language(tmp_path)
    assert result == "mixed"


# ── read_file_safe ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_read_file_safe_truncates(tmp_path):
    """Files larger than max_chars are truncated and marked."""
    big_file = tmp_path / "big.py"
    big_file.write_text("x" * 500)
    result = fu.read_file_safe(big_file, max_chars=100)
    assert len(result) == len("x" * 100 + "\n// ... (truncated)")
    assert result.endswith("// ... (truncated)")


@pytest.mark.unit
def test_read_file_safe_no_truncation_when_small(tmp_path):
    """Small files are returned unchanged."""
    small_file = tmp_path / "small.py"
    small_file.write_text("x = 1\n")
    result = fu.read_file_safe(small_file, max_chars=8000)
    assert result == "x = 1\n"
    assert "truncated" not in result


# ── get_changed_files ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_changed_files_returns_existing_files(tmp_path):
    """get_changed_files returns only files that actually exist on disk."""
    (tmp_path / "existing.py").write_text("x = 1")
    # deleted.py is in git output but does not exist on disk

    mock_result = MagicMock(returncode=0, stdout="existing.py\ndeleted.py\n")
    with patch("subprocess.run", return_value=mock_result):
        result = get_changed_files(tmp_path)

    assert result is not None
    assert len(result) == 1
    assert result[0].name == "existing.py"


@pytest.mark.unit
def test_get_changed_files_empty_diff(tmp_path):
    """Empty git diff output → empty list (not None)."""
    mock_result = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        result = get_changed_files(tmp_path)
    assert result == []


@pytest.mark.unit
def test_get_changed_files_not_git_repo(tmp_path):
    """Non-zero returncode (not a git repo) → None."""
    mock_result = MagicMock(returncode=128, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        result = get_changed_files(tmp_path)
    assert result is None


# ── get_staged_files ────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_staged_files_returns_staged(tmp_path):
    """get_staged_files calls git diff --cached and returns existing files."""
    (tmp_path / "staged.py").write_text("y = 2")
    mock_result = MagicMock(returncode=0, stdout="staged.py\n")
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = get_staged_files(tmp_path)

    assert result is not None
    assert len(result) == 1
    assert result[0].name == "staged.py"
    called_cmd = mock_run.call_args[0][0]
    assert "--cached" in called_cmd


# ── detect_language edge cases ──────────────────────────────────────────────────

@pytest.mark.unit
def test_detect_language_empty_dir(tmp_path):
    """Empty directory → 'unknown'."""
    result = detect_language(tmp_path)
    assert result == "unknown"


# ── read_file_safe error handling ───────────────────────────────────────────────

@pytest.mark.unit
def test_read_file_safe_oserror_returns_empty(tmp_path):
    """OSError during read_text → returns empty string, no exception raised."""
    f = tmp_path / "unreadable.py"
    f.write_text("x = 1")
    # read_file_safe uses path.read_text(), so patch at that level
    with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
        result = read_file_safe(f)
    assert result == "" or result is None


# ── discover_files cache ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_discovery_cache_hit(tmp_path):
    """Second discover_files call on same path returns cached result."""
    (tmp_path / "a.py").write_text("x=1")
    fu._DISCOVERY_CACHE.clear()
    result1 = fu.discover_files(tmp_path, [".py"])
    result2 = fu.discover_files(tmp_path, [".py"])
    assert result1 == result2
    # Both calls should have populated / used the same cache key
    assert len(fu._DISCOVERY_CACHE) >= 1


@pytest.mark.unit
def test_discover_files_single_file(tmp_path):
    """discover_files on a single file path (not a directory) returns that file."""
    f = tmp_path / "mod.py"
    f.write_text("x = 1")
    fu._DISCOVERY_CACHE.clear()
    result = fu.discover_files(f, [".py"])
    assert len(result) == 1
    assert result[0] == f


# ── get_branch_files ────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_branch_files_nonzero_returns_none(tmp_path):
    """Non-zero returncode (not a git repo / diff failed) → None."""
    mock_result = MagicMock(returncode=128, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        result = fu.get_branch_files(tmp_path, base="main")
    assert result is None


@pytest.mark.unit
def test_get_branch_files_exception_returns_none(tmp_path):
    """subprocess raises → None (not an exception propagated to caller)."""
    with patch("subprocess.run", side_effect=Exception("git not found")):
        result = fu.get_branch_files(tmp_path, base="main")
    assert result is None


@pytest.mark.unit
def test_get_branch_files_filters_nonexistent_files(tmp_path):
    """get_branch_files only returns files that actually exist on disk."""
    (tmp_path / "existing.py").write_text("x = 1")
    # deleted.py is in git output but was deleted
    mock_result = MagicMock(returncode=0, stdout="existing.py\ndeleted.py\n")
    with patch("subprocess.run", return_value=mock_result):
        result = fu.get_branch_files(tmp_path, base="main")
    assert result is not None
    assert len(result) == 1
    assert result[0].name == "existing.py"


@pytest.mark.unit
def test_get_branch_files_empty_diff_returns_empty_list(tmp_path):
    """Empty git diff output (no changed files on branch) → [] not None."""
    mock_result = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        result = fu.get_branch_files(tmp_path, base="main")
    assert result == []


@pytest.mark.unit
def test_get_branch_files_uses_three_dot_diff(tmp_path):
    """get_branch_files uses the three-dot diff syntax (base...HEAD)."""
    mock_result = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        fu.get_branch_files(tmp_path, base="main")
    cmd = mock_run.call_args[0][0]
    assert "main...HEAD" in cmd
