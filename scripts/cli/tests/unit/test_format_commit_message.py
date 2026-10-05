#!/usr/bin/env python3
"""Tests for format_commit_message.py"""

import argparse
import json
from unittest.mock import patch

import pytest
from cli.format_commit_message import (
    FormatCommitMessageScript,
    format_commit_message,
    generate_suggestion,
    validate_commit_message,
)


def test_validate_commit_message_valid():
    """Test validation of valid commit message."""
    result = validate_commit_message("#123: feat: add authentication")
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_commit_message_missing_issue():
    """Test validation with missing issue ID."""
    result = validate_commit_message("feat: add feature")
    assert result.valid is False
    assert any("issue" in e.lower() for e in result.errors)


def test_validate_commit_message_missing_type():
    """Test validation with missing type."""
    result = validate_commit_message("#123: add feature")
    assert result.valid is False
    assert any("type" in e.lower() for e in result.errors)


def test_validate_commit_message_too_short():
    """Test validation with too short message."""
    # "#123: feat: ab" has only 2 char description (< 3 required by regex), so invalid
    result = validate_commit_message("#123: feat: ab")
    assert result.valid is False


def test_validate_commit_message_uppercase_warning():
    """Test validation warns about uppercase description."""
    result = validate_commit_message("#123: feat: Add Feature")
    assert any("lowercase" in w.lower() for w in result.warnings)


def test_validate_commit_message_period_warning():
    """Test validation warns about trailing period."""
    result = validate_commit_message("#123: feat: add feature.")
    assert any("period" in w.lower() for w in result.warnings)


def test_validate_commit_message_past_tense_warning():
    """Test validation warns about past tense."""
    result = validate_commit_message("#123: feat: added feature")
    assert any("imperative" in w.lower() for w in result.warnings)


def test_generate_suggestion_simple():
    """Test suggestion generation for simple case."""
    suggestion = generate_suggestion("#123 added authentication")
    assert suggestion == "#123: feat: add authentication"


def test_generate_suggestion_with_type():
    """Test suggestion generation when type is present."""
    suggestion = generate_suggestion("#123 fix: fixed bug")
    assert suggestion == "#123: fix: fix bug"


def test_generate_suggestion_infer_fix():
    """Test suggestion generation infers 'fix' type."""
    suggestion = generate_suggestion("#123 resolve login issue")
    assert "fix" in suggestion


def test_generate_suggestion_infer_refactor():
    """Test suggestion generation infers 'refactor' type."""
    suggestion = generate_suggestion("#123 refactor code structure")
    assert "refactor" in suggestion


def test_generate_suggestion_infer_test():
    """Test suggestion generation infers 'test' type."""
    suggestion = generate_suggestion("#123 add tests for auth")
    assert "test" in suggestion


def test_generate_suggestion_infer_docs():
    """Test suggestion generation infers 'docs' type."""
    suggestion = generate_suggestion("#123 update readme")
    assert "docs" in suggestion


def test_generate_suggestion_no_issue():
    """Test suggestion generation without issue."""
    suggestion = generate_suggestion("added feature")
    assert suggestion is None


def test_validate_with_suggest():
    """Test validation with suggestion enabled."""
    result = validate_commit_message("#123 added feature", suggest=True)
    assert result.valid is False
    assert result.suggestion is not None
    assert "#123:" in result.suggestion
    assert "feat:" in result.suggestion


def test_validate_azure_format():
    """Test validation with Azure DevOps format."""
    result = validate_commit_message("#12345: fix: resolve issue")
    assert result.valid is True


# ── formatting mode and the script (GitHub issue format pinned) ──────────────


@pytest.fixture
def github():
    with patch("cli.format_commit_message.get_issue_format", return_value=r"#\d+"):
        yield


def test_format_commit_message_strips_whitespace_and_period():
    assert format_commit_message("#1", "feat", " add parser. ") == "#1: feat: add parser"


@pytest.mark.xfail(
    strict=True,
    reason="bug (#51): the lowercase condition is inverted, so 'Add' keeps its capital (and 'README' becomes 'rEADME')",
)
def test_format_commit_message_lowercases_first_letter():
    assert format_commit_message("#1", "feat", "Add parser") == "#1: feat: add parser"


def test_generate_suggestion_infers_chore():
    assert generate_suggestion("#7 bump the version.") == "#7: chore: bump the version"


@pytest.mark.xfail(
    strict=True,
    reason="bug (#51): the type regex has no word boundary, so 'ci' inside 'dependencies' is taken as the type",
)
def test_generate_suggestion_ignores_type_names_inside_words():
    assert generate_suggestion("#7 bump dependencies") == "#7: chore: bump dependencies"


def test_generate_suggestion_converts_created_and_updated():
    assert generate_suggestion("#7 created and updated the index") == "#7: feat: create and update the index"


def _run(argv, capsys):
    FormatCommitMessageScript().run(argv)
    return capsys.readouterr().out.rstrip("\n")


@pytest.mark.usefixtures("github")
def test_script_validate_json(capsys):
    data = json.loads(_run(["--message", "#3 added things.", "--suggest"], capsys))
    assert data["mode"] == "validate"
    assert data["valid"] is False
    assert data["suggestion"] == "#3: feat: add things"
    assert "Description should not end with period" in data["warnings"]


@pytest.mark.usefixtures("github")
def test_script_validate_text_lists_errors_warnings_and_suggestion(capsys):
    text = _run(["--message", "#3 added things.", "--suggest", "--format", "text"], capsys)
    lines = text.splitlines()
    assert lines[0] == "[FAIL] Invalid commit message"
    assert "Errors:" in lines and "Warnings:" in lines
    assert any(line.startswith("  [X] Missing or invalid type") for line in lines)
    assert any(line.startswith("  [!] Use imperative mood") for line in lines)
    assert lines[-1] == "Suggestion: #3: feat: add things"


@pytest.mark.usefixtures("github")
def test_script_validate_text_for_valid_message(capsys):
    assert _run(["--message", "#3: fix: handle empty input", "--format", "text"], capsys) == (
        "[OK] Valid commit message"
    )


@pytest.mark.usefixtures("github")
def test_script_validate_summary(capsys):
    assert _run(["--message", "#3: fix: handle empty input", "--format", "summary"], capsys) == (
        "[OK] 0 errors, 0 warnings"
    )


@pytest.mark.usefixtures("github")
def test_script_format_mode_text_and_summary(capsys):
    argv = ["--message", "handle empty input.", "--issue", "#4", "--type", "fix"]
    assert _run(argv + ["--format", "text"], capsys) == (
        "Original: handle empty input.\nFormatted: #4: fix: handle empty input\nValid: Yes"
    )
    assert _run(argv + ["--format", "summary"], capsys) == "#4: fix: handle empty input"


def test_script_reports_errors(capsys):
    with patch("cli.format_commit_message.get_issue_format", side_effect=RuntimeError("no profile")):
        result = FormatCommitMessageScript().execute(
            argparse.Namespace(message="m", validate=True, suggest=False, issue=None, type=None)
        )
    assert result == {"success": False, "error": "no profile"}
    script = FormatCommitMessageScript()
    assert script.format_text(result) == "Error: no profile"
    assert script.format_summary(result) == "[ERROR] no profile"
