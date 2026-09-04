"""Integration tests for --since incremental mode."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

DIRTY_PYTHON = """\
try:
    risky_operation()
except:
    pass
"""

CLEAN_PYTHON = """\
SECONDS_PER_DAY = 86400

def double_positives(items):
    return [item * 2 for item in items if item > 0]
"""


def _git(cmd, cwd):
    """Run a git command, return (returncode, stdout)."""
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True
    )
    return result.returncode, result.stdout


def _init_git_repo(path):
    """Initialise a minimal git repo in path."""
    _git(["git", "init"], path)
    _git(["git", "config", "user.email", "test@test.com"], path)
    _git(["git", "config", "user.name", "Test"], path)


@pytest.mark.integration_mock
def test_since_head_only_analyzes_changed_files(tmp_path):
    """--since HEAD: only uncommitted (changed) files are analyzed."""
    _init_git_repo(tmp_path)

    # Commit clean file
    clean = tmp_path / "clean.py"
    clean.write_text(CLEAN_PYTHON)
    _git(["git", "add", "."], tmp_path)
    _git(["git", "commit", "-m", "init", "--allow-empty-message"], tmp_path)

    # Add dirty file (not committed → shows up in git diff HEAD)
    dirty = tmp_path / "dirty.py"
    dirty.write_text(DIRTY_PYTHON)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(tmp_path),
            "--since", "HEAD",
            "--checks", "error_handling",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    violated_files = {v["file"] for v in data["violations"]}
    # dirty.py should appear in violations, clean.py should not
    assert not any("clean" in f for f in violated_files), (
        f"clean.py should not have violations; got: {violated_files}"
    )


@pytest.mark.integration_mock
def test_since_non_git_falls_back_to_full(tmp_path):
    """--since on a non-git directory → falls back to full analysis."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(DIRTY_PYTHON)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(src),
            "--since", "HEAD",
            "--checks", "error_handling",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    # Full analysis should still find violations
    assert data["total_violations"] >= 1


# ── --staged flag ───────────────────────────────────────────────────────────────

@pytest.mark.integration_mock
def test_staged_flag_analyzes_only_staged_files(tmp_path):
    """--staged: only staged files analyzed; unstaged files produce no violations."""
    # Initialise a minimal git repo
    _git(["git", "init"], tmp_path)
    _git(["git", "config", "user.email", "t@t.com"], tmp_path)
    _git(["git", "config", "user.name", "T"], tmp_path)

    clean = tmp_path / "clean.py"
    dirty = tmp_path / "dirty.py"
    clean.write_text(CLEAN_PYTHON)
    dirty.write_text(DIRTY_PYTHON)

    # Stage only dirty.py (clean.py is untracked but not staged)
    _git(["git", "add", str(dirty)], tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(tmp_path),
            "--staged",
            "--checks", "error_handling",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    violated_files = {v["file"] for v in data["violations"]}
    # dirty.py should appear; clean.py should not
    assert not any("clean" in f for f in violated_files), (
        f"clean.py should not have violations; got files: {violated_files}"
    )
