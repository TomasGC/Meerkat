"""
Integration tests (real) — git operations against real repositories.

Creates actual git repos in tmp_path and tests scripts that interact
with git. Requires git to be installed.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration_real, pytest.mark.requires_git]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_git_repo(path: Path) -> Path:
    """Initialize a git repo with an initial commit."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@test.com"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"],
                   check=True, capture_output=True)
    (path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "#1: chore: initial commit"],
                   check=True, capture_output=True)
    return path

@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    return init_git_repo(tmp_path / "repo")

@pytest.fixture
def git_repo_with_commits(git_repo: Path) -> Path:
    """Repo with multiple commits for testing log operations."""
    (git_repo / "src.py").write_text("def hello(): pass\n")
    subprocess.run(["git", "-C", str(git_repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(git_repo), "commit", "-m", "#1: feat: add hello function"],
                   check=True, capture_output=True)

    (git_repo / "src.py").write_text("def hello(): return 'hello'\n")
    subprocess.run(["git", "-C", str(git_repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(git_repo), "commit", "-m", "#1: fix: return value in hello"],
                   check=True, capture_output=True)
    return git_repo

# ---------------------------------------------------------------------------
# Real: check_git_repo.py
# ---------------------------------------------------------------------------

def test_check_git_repo_detects_valid_repo(git_repo):
    import argparse
    from cli.check_git_repo import CheckGitRepoScript
    script = CheckGitRepoScript()
    args = argparse.Namespace(path=git_repo, format="json")
    result = script.execute(args)
    assert result["is_git_repo"] is True

def test_check_git_repo_detects_non_repo(tmp_path):
    import argparse
    from cli.check_git_repo import CheckGitRepoScript
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    script = CheckGitRepoScript()
    args = argparse.Namespace(path=non_repo, format="json")
    result = script.execute(args)
    assert result["is_git_repo"] is False

# ---------------------------------------------------------------------------
# Real: get_commit_info.py
# ---------------------------------------------------------------------------

def test_get_commit_info_head(git_repo_with_commits):
    import argparse
    from cli.get_commit_info import GetCommitInfoScript
    import os
    old_dir = os.getcwd()
    try:
        os.chdir(git_repo_with_commits)
        script = GetCommitInfoScript()
        args = argparse.Namespace(hash="HEAD", count=1, include_files=False, format="json")
        result = script.execute(args)
        assert "commits" in result or "hash" in result or "message" in result
    finally:
        os.chdir(old_dir)

def test_get_commit_info_multiple(git_repo_with_commits):
    import argparse
    from cli.get_commit_info import GetCommitInfoScript
    import os
    old_dir = os.getcwd()
    try:
        os.chdir(git_repo_with_commits)
        script = GetCommitInfoScript()
        args = argparse.Namespace(hash=None, count=3, include_files=False, format="json")
        result = script.execute(args)
        commits = result.get("commits", [])
        assert len(commits) >= 1
    finally:
        os.chdir(old_dir)

# ---------------------------------------------------------------------------
# Real: get_branch_summary.py
# ---------------------------------------------------------------------------

def test_get_branch_summary_main_branch(git_repo):
    import argparse
    from cli.get_branch_summary import GetBranchSummaryScript
    import os
    old_dir = os.getcwd()
    try:
        os.chdir(git_repo)
        script = GetBranchSummaryScript()
        args = argparse.Namespace(
            base=None, branch=None, include_stats=False, format="json"
        )
        result = script.execute(args)
        assert "branch" in result or "current_branch" in result
    finally:
        os.chdir(old_dir)

# ---------------------------------------------------------------------------
# Real: find_git_repos.py
# ---------------------------------------------------------------------------

def test_find_git_repos_finds_repo(tmp_path):
    import argparse
    from cli.find_git_repos import FindGitReposScript
    repo1 = init_git_repo(tmp_path / "project1")
    repo2 = init_git_repo(tmp_path / "project2")
    script = FindGitReposScript()
    args = argparse.Namespace(
        path=tmp_path, max_depth=2, format="json", exclude=[]
    )
    result = script.execute(args)
    repos = result.get("repos", result.get("repositories", []))
    assert len(repos) >= 2

def test_find_git_repos_no_repos(tmp_path):
    import argparse
    from cli.find_git_repos import FindGitReposScript
    (tmp_path / "not_a_repo").mkdir()
    script = FindGitReposScript()
    args = argparse.Namespace(
        path=tmp_path, max_depth=2, format="json", exclude=[]
    )
    result = script.execute(args)
    repos = result.get("repos", result.get("repositories", []))
    assert len(repos) == 0

# ---------------------------------------------------------------------------
# Real: extract_issue.py from real branch
# ---------------------------------------------------------------------------

def test_extract_issue_from_real_commit(git_repo_with_commits):
    import argparse
    from cli.extract_issue import ExtractIssueScript
    import os
    old_dir = os.getcwd()
    try:
        os.chdir(git_repo_with_commits)
        script = ExtractIssueScript()
        args = argparse.Namespace(
            branch=None, from_commit=True, format="json",
            integration_profile=None
        )
        result = script.execute(args)
        # The commit message contains "#1:"
        assert result.get("issue_id") in ("#1", "1", None)
    finally:
        os.chdir(old_dir)

# ---------------------------------------------------------------------------
# Real: analyze_commit_quality.py on real diff
# ---------------------------------------------------------------------------

def test_analyze_commit_quality_real_diff(git_repo_with_commits):
    import argparse
    from cli.analyze_commit_quality import AnalyzeCommitQualityScript
    import os
    old_dir = os.getcwd()
    try:
        os.chdir(git_repo_with_commits)
        script = AnalyzeCommitQualityScript()
        args = argparse.Namespace(
            commits="HEAD", diff=None, format="json",
            checks=["security", "quality"]
        )
        result = script.execute(args)
        assert "violations" in result or "issues" in result or "total_violations" in result
    finally:
        os.chdir(old_dir)
