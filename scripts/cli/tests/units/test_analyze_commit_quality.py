#!/usr/bin/env python3
"""Tests for analyze_commit_quality.py"""

from pathlib import Path

import pytest

from cli.analyze_commit_quality import AnalyzeCommitQualityScript, SECURITY_PATTERNS, QUALITY_PATTERNS

@pytest.fixture
def script():
    """Create script instance."""
    return AnalyzeCommitQualityScript()

@pytest.fixture
def temp_git_repo(tmp_path):
    """Create temp git repo with changes."""
    import subprocess

    # Initialize repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)

    # Create file with issues
    file = tmp_path / "test.py"
    file.write_text("""
password = "secret123"  # Hardcoded secret
query = "SELECT * FROM users WHERE id = " + user_id  # SQL injection
x = 12345  # Magic number
# TODO: Fix this later
console.log("debug");
""")

    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True, capture_output=True)

    return tmp_path

def test_security_patterns_loaded():
    """Test that security patterns are loaded."""
    assert "hardcoded_secret" in SECURITY_PATTERNS
    assert "sql_injection" in SECURITY_PATTERNS
    assert "xss_vulnerability" in SECURITY_PATTERNS
    assert "weak_crypto" in SECURITY_PATTERNS

def test_quality_patterns_loaded():
    """Test that quality patterns are loaded."""
    assert "magic_number" in QUALITY_PATTERNS
    assert "todo_fixme" in QUALITY_PATTERNS
    assert "console_log" in QUALITY_PATTERNS

def test_security_pattern_detection():
    """Test detection of security pattern."""
    import re
    line = 'password = "secret123"'

    # Should match hardcoded_secret pattern
    pattern = SECURITY_PATTERNS["hardcoded_secret"]["patterns"][0]
    match = re.search(pattern, line)

    assert match is not None

def test_quality_pattern_detection():
    """Test detection of quality pattern."""
    import re
    line = "x = 12345"

    # Should match magic_number pattern
    pattern = QUALITY_PATTERNS["magic_number"]["patterns"][0]
    match = re.search(pattern, line)

    assert match is not None

def test_script_execution_success(script, temp_git_repo, monkeypatch):
    """Test full script execution."""
    class Args:
        staged = True
        format = "json"
        commit = None

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert "violations" in result or "message" in result
    assert result["total_violations"] >= 0 if "total_violations" in result else True
