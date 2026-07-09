#!/usr/bin/env python3
"""Tests for extract_issue.py"""

from pathlib import Path
from unittest.mock import patch

import pytest

from cli.extract_issue import extract_issue_from_text

@patch('cli.extract_issue.get_issue_format')
def test_extract_issue_github_format(mock_get_format):
    """Test extraction of issue ID (GitHub format)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "feature/#123-add-feature"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#123"

@patch('cli.extract_issue.get_issue_format')
def test_extract_issue_generic_format(mock_get_format):
    """Test extraction of issue ID (Jira format)."""
    mock_get_format.return_value = r"([A-Z]{2,}-\d+)"

    text = "bugfix/PROJ-456-fix-bug"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "PROJ-456"

@patch('cli.extract_issue.get_issue_format')
def test_extract_issue_from_commit_message(mock_get_format):
    """Test extraction from commit message (GitHub format)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "#789: feat: add new feature"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#789"

@patch('cli.extract_issue.get_issue_format')
def test_extract_issue_no_ticket(mock_get_format):
    """Test extraction of issue ID present."""
    mock_get_format.return_value = r"#(\d+)"

    text = "main"
    issue_id = extract_issue_from_text(text)
    assert issue_id is None

@patch('cli.extract_issue.get_issue_format')
def test_extract_issue_multiple_matches(mock_get_format):
    """Test extraction of issue IDs (returns first)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "feature/#123-and-#456"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#123"

