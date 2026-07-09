#!/usr/bin/env python3
"""Tests for format_commit_message.py"""

from pathlib import Path

import pytest

from cli.format_commit_message import (
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
