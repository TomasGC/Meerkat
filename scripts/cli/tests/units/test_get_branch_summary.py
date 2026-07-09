#!/usr/bin/env python3
"""Tests for get_branch_summary.py"""

from pathlib import Path
from unittest.mock import patch

import pytest

from cli.get_branch_summary import (
    get_current_branch,
    get_default_base_branch)
from common.models import BranchCommit, BranchSummary, FileChange, UncommittedChanges

def test_get_default_base_branch_main():
    """Test detecting main as default branch."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        # Mock: origin remote exists
        mock_run.side_effect = [
            (0, "origin\n", ""),  # git remote
            (1, "", ""),  # git symbolic-ref (fails)
            (0, "origin/main\norigin/feature\n", "")  # git branch -r
        ]

        result = get_default_base_branch()
        assert result == "main"

def test_get_default_base_branch_master():
    """Test detecting master as default branch."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.side_effect = [
            (0, "origin\n", ""),
            (1, "", ""),
            (0, "origin/master\norigin/feature\n", "")
        ]

        result = get_default_base_branch()
        assert result == "master"

def test_get_default_base_branch_fallback():
    """Test fallback to main when no remote."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.return_value = (1, "", "")

        result = get_default_base_branch()
        assert result == "main"

def test_get_current_branch():
    """Test getting current branch."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.return_value = (0, "feature/#123\n", "")

        result = get_current_branch()
        assert result == "feature/#123"

def test_get_current_branch_error():
    """Test error when not in git repo."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.return_value = (1, "", "fatal: not a git repository")

        with pytest.raises(RuntimeError, match="(?i)not in a git repository"):
            get_current_branch()

def test_get_current_branch_detached():
    """Test error when detached HEAD."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.return_value = (0, "", "")

        with pytest.raises(RuntimeError, match="detached HEAD"):
            get_current_branch()
