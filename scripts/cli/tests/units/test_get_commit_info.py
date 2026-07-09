#!/usr/bin/env python3
"""Tests for get_commit_info.py"""

from pathlib import Path

import pytest

from cli.get_commit_info import (
    get_commit_files,
    get_commit_info)
from common.models import GitCommitInfo

def test_get_commit_info_head():
    """Test getting HEAD commit."""
    commits = get_commit_info("HEAD", count=1, include_files=False)

    assert len(commits) == 1
    assert commits[0].hash
    assert commits[0].author
    assert commits[0].date
    assert commits[0].message

def test_get_commit_info_multiple():
    """Test getting multiple commits."""
    commits = get_commit_info("HEAD", count=3, include_files=False)

    assert len(commits) >= 1  # May have fewer if repo has < 3 commits
    for commit in commits:
        assert commit.hash
        assert commit.author
        assert commit.message

def test_get_commit_info_with_files():
    """Test getting commit with file changes."""
    commits = get_commit_info("HEAD", count=1, include_files=True)

    assert len(commits) == 1
    # Files may be empty if commit has no changes
    assert isinstance(commits[0].files_changed, list)
    assert isinstance(commits[0].insertions, int)
    assert isinstance(commits[0].deletions, int)

def test_get_commit_info_invalid_hash():
    """Test with invalid commit hash."""
    with pytest.raises(RuntimeError, match="Git log failed"):
        get_commit_info("nonexistent123456", count=1)

def test_get_commit_files_head():
    """Test getting files changed in HEAD commit."""
    commits = get_commit_info("HEAD", count=1, include_files=False)
    hash = commits[0].hash

    files, insertions, deletions = get_commit_files(hash)

    # Files may be empty if no changes
    assert isinstance(files, list)
    assert isinstance(insertions, int)
    assert isinstance(deletions, int)
    assert insertions >= 0
    assert deletions >= 0

def test_get_commit_files_invalid_hash():
    """Test getting files with invalid hash."""
    files, insertions, deletions = get_commit_files("invalid123456")

    assert files == []
    assert insertions == 0
    assert deletions == 0
