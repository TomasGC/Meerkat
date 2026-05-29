#!/usr/bin/env python3
"""Tests for find_git_repos.py"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from cli.find_git_repos import find_git_repos, get_repo_info
from common.utils import run_command, write_file_safe

@pytest.fixture
def multi_repo_structure(tmp_path):
    """Create a directory structure with multiple git repositories."""
    # Create directory structure
    # /
    # ├── repo1/
    # │   └── .git/
    # ├── repo2/
    # │   └── .git/
    # ├── projects/
    # │   ├── repo3/
    # │   │   └── .git/
    # │   └── repo4/
    # │       └── .git/
    # └── not-a-repo/

    repos = []

    # Create repo1
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    run_command(["git", "init"], cwd=repo1, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo1, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=repo1, timeout=5)
    readme = repo1 / "README.md"
    write_file_safe(readme, "# Repo 1")
    run_command(["git", "add", "README.md"], cwd=repo1, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo1, timeout=5)
    repos.append(repo1)

    # Create repo2 with remote
    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    run_command(["git", "init"], cwd=repo2, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo2, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=repo2, timeout=5)
    run_command(["git", "remote", "add", "origin", "https://github.com/test/repo2.git"], cwd=repo2, timeout=5)
    readme = repo2 / "README.md"
    write_file_safe(readme, "# Repo 2")
    run_command(["git", "add", "README.md"], cwd=repo2, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo2, timeout=5)
    repos.append(repo2)

    # Create projects directory
    projects = tmp_path / "projects"
    projects.mkdir()

    # Create repo3 in projects/
    repo3 = projects / "repo3"
    repo3.mkdir()
    run_command(["git", "init"], cwd=repo3, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo3, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=repo3, timeout=5)
    readme = repo3 / "README.md"
    write_file_safe(readme, "# Repo 3")
    run_command(["git", "add", "README.md"], cwd=repo3, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo3, timeout=5)
    repos.append(repo3)

    # Create repo4 in projects/
    repo4 = projects / "repo4"
    repo4.mkdir()
    run_command(["git", "init"], cwd=repo4, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=repo4, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=repo4, timeout=5)
    readme = repo4 / "README.md"
    write_file_safe(readme, "# Repo 4")
    run_command(["git", "add", "README.md"], cwd=repo4, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo4, timeout=5)
    repos.append(repo4)

    # Create non-repo directory
    not_repo = tmp_path / "not-a-repo"
    not_repo.mkdir()

    return tmp_path, repos

def test_find_git_repos_finds_all(multi_repo_structure):
    """Test finding all repositories."""
    root, expected_repos = multi_repo_structure

    repos = find_git_repos(root, max_depth=-1)

    assert len(repos) == 4
    found_paths = {Path(r["path"]) for r in repos}
    expected_paths = set(expected_repos)
    assert found_paths == expected_paths

def test_find_git_repos_max_depth_1(multi_repo_structure):
    """Test max depth of 1 level."""
    root, expected_repos = multi_repo_structure

    repos = find_git_repos(root, max_depth=1)

    # Should find repo1 and repo2, but not repo3/repo4 (deeper)
    assert len(repos) == 2
    found_names = {r["name"] for r in repos}
    assert found_names == {"repo1", "repo2"}

def test_find_git_repos_max_depth_2(multi_repo_structure):
    """Test max depth of 2 levels."""
    root, expected_repos = multi_repo_structure

    repos = find_git_repos(root, max_depth=2)

    # Should find all 4 repos
    assert len(repos) == 4

def test_find_git_repos_sorted(multi_repo_structure):
    """Test that results are sorted by path."""
    root, expected_repos = multi_repo_structure

    repos = find_git_repos(root, max_depth=-1)

    # Verify sorting
    paths = [r["path"] for r in repos]
    assert paths == sorted(paths)

def test_find_git_repos_empty_directory(tmp_path):
    """Test searching empty directory."""
    repos = find_git_repos(tmp_path, max_depth=-1)

    assert repos == []

def test_find_git_repos_no_git_repos(tmp_path):
    """Test directory with no git repos."""
    # Create some directories without .git
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir2").mkdir()

    repos = find_git_repos(tmp_path, max_depth=-1)

    assert repos == []

def test_get_repo_info_basic(tmp_path):
    """Test getting basic repository info."""
    # Create repo
    run_command(["git", "init"], cwd=tmp_path, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=tmp_path, timeout=5)
    readme = tmp_path / "README.md"
    write_file_safe(readme, "# Test")
    run_command(["git", "add", "README.md"], cwd=tmp_path, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=tmp_path, timeout=5)

    info = get_repo_info(tmp_path)

    assert info["path"] == str(tmp_path)
    assert info["name"] == tmp_path.name
    assert info["branch"] in ["master", "main"] or info["branch"] is None
    assert info["hasRemote"] is False

def test_get_repo_info_with_remote(tmp_path):
    """Test getting repo info with remote."""
    # Create repo with remote
    run_command(["git", "init"], cwd=tmp_path, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=tmp_path, timeout=5)
    run_command(["git", "remote", "add", "origin", "https://github.com/test/repo.git"], cwd=tmp_path, timeout=5)
    readme = tmp_path / "README.md"
    write_file_safe(readme, "# Test")
    run_command(["git", "add", "README.md"], cwd=tmp_path, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=tmp_path, timeout=5)

    info = get_repo_info(tmp_path)

    assert info["hasRemote"] is True
    assert info["remote"] == "origin"
    assert info["remoteUrl"] == "https://github.com/test/repo.git"


def test_find_git_repos_nested_repos(tmp_path):
    """Test handling of nested repositories."""
    # Create parent repo
    parent = tmp_path / "parent"
    parent.mkdir()
    run_command(["git", "init"], cwd=parent, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=parent, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=parent, timeout=5)
    readme = parent / "README.md"
    write_file_safe(readme, "# Parent")
    run_command(["git", "add", "README.md"], cwd=parent, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=parent, timeout=5)

    # Create nested repo
    nested = parent / "nested"
    nested.mkdir()
    run_command(["git", "init"], cwd=nested, timeout=5)
    run_command(["git", "config", "user.email", "test@test.com"], cwd=nested, timeout=5)
    run_command(["git", "config", "user.name", "Test"], cwd=nested, timeout=5)
    readme = nested / "README.md"
    write_file_safe(readme, "# Nested")
    run_command(["git", "add", "README.md"], cwd=nested, timeout=5)
    run_command(["git", "commit", "-m", "Initial"], cwd=nested, timeout=5)

    repos = find_git_repos(tmp_path, max_depth=-1)

    # Should find both parent and nested
    assert len(repos) == 2
    found_names = {r["name"] for r in repos}
    assert found_names == {"parent", "nested"}

def test_find_git_repos_max_depth_0(multi_repo_structure):
    """Test max depth of 0 (search only root)."""
    root, expected_repos = multi_repo_structure

    repos = find_git_repos(root, max_depth=0)

    # Should find nothing (no repos in root itself)
    assert repos == []

def test_get_repo_info_no_commits(tmp_path):
    """Test repo info for repository with no commits."""
    # Create empty repo
    run_command(["git", "init"], cwd=tmp_path, timeout=5)

    info = get_repo_info(tmp_path)

    assert info["path"] == str(tmp_path)
    # Git may have default branch (master/main) even without commits
    assert info["branch"] is None or info["branch"] == "" or info["branch"] in ["master", "main"]
    assert info["hasRemote"] is False
