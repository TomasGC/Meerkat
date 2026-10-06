#!/usr/bin/env python3
"""Tests for extract_issue.py"""

import json
from unittest.mock import patch

import pytest

from cli.extract_issue import (
    ExtractTicketScript,
    extract_issue,
    extract_issue_from_text,
    get_current_branch,
    get_last_commit_message,
)


@patch("cli.extract_issue.get_issue_format")
def test_extract_issue_github_format(mock_get_format):
    """Test extraction of issue ID (GitHub format)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "feature/#123-add-feature"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#123"


@patch("cli.extract_issue.get_issue_format")
def test_extract_issue_generic_format(mock_get_format):
    """Test extraction of issue ID (Jira format)."""
    mock_get_format.return_value = r"([A-Z]{2,}-\d+)"

    text = "bugfix/PROJ-456-fix-bug"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "PROJ-456"


@patch("cli.extract_issue.get_issue_format")
def test_extract_issue_from_commit_message(mock_get_format):
    """Test extraction from commit message (GitHub format)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "#789: feat: add new feature"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#789"


@patch("cli.extract_issue.get_issue_format")
def test_extract_issue_no_ticket(mock_get_format):
    """Test extraction of issue ID present."""
    mock_get_format.return_value = r"#(\d+)"

    text = "main"
    issue_id = extract_issue_from_text(text)
    assert issue_id is None


@patch("cli.extract_issue.get_issue_format")
def test_extract_issue_multiple_matches(mock_get_format):
    """Test extraction of issue IDs (returns first)."""
    mock_get_format.return_value = r"#(\d+)"

    text = "feature/#123-and-#456"
    issue_id = extract_issue_from_text(text)
    assert issue_id == "#123"


# ── git sources and script (run_command mocked) ──────────────────────────────


def _git(cmd, **_kwargs):
    return {
        ("git", "branch", "--show-current"): (0, "feature/#12-login\n", ""),
        ("git", "log", "-1", "--pretty=%B"): (0, "#34: fix: token refresh\n", ""),
    }.get(tuple(cmd), (1, "", ""))


@pytest.fixture
def github_format():
    with patch("cli.extract_issue.get_issue_format", return_value=r"#(\d+)"):
        yield


@pytest.mark.usefixtures("github_format")
def test_extract_issue_from_current_branch():
    with patch("cli.extract_issue.run_command", side_effect=_git):
        assert extract_issue() == "#12"


@pytest.mark.usefixtures("github_format")
def test_extract_issue_from_last_commit():
    with patch("cli.extract_issue.run_command", side_effect=_git):
        assert extract_issue(from_commit=True) == "#34"


@pytest.mark.usefixtures("github_format")
def test_extract_issue_from_given_branch_needs_no_git():
    with patch("cli.extract_issue.run_command") as run:
        assert extract_issue(branch="bugfix/#56-x") == "#56"
    run.assert_not_called()


def test_git_failures_raise():
    with patch("cli.extract_issue.run_command", return_value=(128, "", "")):
        with pytest.raises(RuntimeError, match="Not a git repository"):
            get_current_branch()
        with pytest.raises(RuntimeError, match="no commits"):
            get_last_commit_message()


def _run(argv, capsys):
    with patch("cli.extract_issue.run_command", side_effect=_git):
        ExtractTicketScript().run(argv)
    return capsys.readouterr().out.strip()


@pytest.mark.usefixtures("github_format")
def test_script_json_from_commit(capsys):
    assert json.loads(_run(["--from-commit"], capsys)) == {"success": True, "issue_id": "#34", "source": "commit"}


@pytest.mark.usefixtures("github_format")
def test_script_text_and_summary(capsys):
    assert _run(["--format", "text"], capsys) == "Issue ID: #12 (source: branch)"
    assert _run(["--branch", "main", "--format", "summary"], capsys) == "No issue ID found"
    assert _run(["--branch", "main", "--format", "text"], capsys) == "No issue ID found"
    assert _run(["--branch", "x/#9", "--format", "summary"], capsys) == "#9"


@pytest.mark.usefixtures("github_format")
def test_script_reports_git_error(capsys):
    with patch("cli.extract_issue.run_command", return_value=(128, "", "")):
        ExtractTicketScript().run(["--format", "summary"])
        ExtractTicketScript().run(["--format", "text"])
    assert capsys.readouterr().out.splitlines() == [
        "[ERROR] Not a git repository",
        "Error: Not a git repository",
    ]
