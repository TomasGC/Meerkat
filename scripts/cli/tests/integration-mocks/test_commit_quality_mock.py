"""
Integration tests (mocked) — commit quality analysis pipeline.

Tests the format_commit_message + analyze_commit_quality pipeline
with mocked git operations.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.format_commit_message import FormatCommitMessageScript
from cli.analyze_commit_quality import AnalyzeCommitQualityScript

pytestmark = pytest.mark.integration_mock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def format_script():
    return FormatCommitMessageScript()

@pytest.fixture
def quality_script():
    return AnalyzeCommitQualityScript()

# ---------------------------------------------------------------------------
# Integration: format_commit_message
# ---------------------------------------------------------------------------

def test_validate_valid_commit(format_script):
    import argparse
    args = argparse.Namespace(
        validate=True,
        suggest=False,
        issue=None,
        type=None,
        message="#1: feat: add user authentication",
        format="json"
    )
    result = format_script.execute(args)
    assert result["valid"] is True

def test_validate_missing_issue(format_script):
    import argparse
    args = argparse.Namespace(
        validate=True, suggest=False, issue=None, type=None,
        message="feat: add user authentication",
        format="json"
    )
    result = format_script.execute(args)
    assert result["valid"] is False
    assert any("issue" in e.lower() for e in result.get("errors", []))

def test_validate_missing_type(format_script):
    import argparse
    args = argparse.Namespace(
        validate=True, suggest=False, issue=None, type=None,
        message="#1: add user authentication",
        format="json"
    )
    result = format_script.execute(args)
    assert result["valid"] is False

def test_suggest_for_invalid_message(format_script):
    import argparse
    args = argparse.Namespace(
        validate=False, suggest=True, issue=None, type=None,
        message="added authentication feature",
        format="json"
    )
    result = format_script.execute(args)
    assert "suggestion" in result

def test_format_with_issue_and_type(format_script):
    import argparse
    args = argparse.Namespace(
        validate=False, suggest=False,
        issue="#42", type="feat",
        message="add user authentication",
        format="json"
    )
    result = format_script.execute(args)
    assert "formatted" in result
    assert "#42" in result["formatted"]
    assert "feat" in result["formatted"]

# ---------------------------------------------------------------------------
# Integration: analyze_commit_quality
# ---------------------------------------------------------------------------

def test_quality_check_clean_diff(quality_script):
    import argparse
    clean_diff = """
diff --git a/src/user.py b/src/user.py
index abc123..def456 100644
--- a/src/user.py
+++ b/src/user.py
@@ -1,3 +1,6 @@
+def create_user(name: str, email: str) -> User:
+    return User(name=name, email=email)
"""
    with patch("cli.analyze_commit_quality.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=clean_diff, stderr="")
        args = argparse.Namespace(
            commits=None, diff=None, format="json",
            checks=["security", "quality"]
        )
        result = quality_script.execute(args)
    assert "violations" in result or "issues" in result or "passed" in result

def test_quality_detects_hardcoded_secret(quality_script):
    import argparse
    diff_with_secret = """
+API_KEY = "sk_live_abc123def456"
+password = "SuperSecret123!"
"""
    with patch("cli.analyze_commit_quality.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=diff_with_secret, stderr="")
        args = argparse.Namespace(
            commits=None, diff=None, format="json",
            checks=["security"]
        )
        result = quality_script.execute(args)
    # Should detect security violations
    violations = result.get("violations", result.get("issues", []))
    assert len(violations) > 0 or result.get("total_violations", 0) > 0

def test_quality_detects_todo_comment(quality_script):
    import argparse
    diff_with_todo = """
+# TODO: fix this later
+def process():
+    pass
"""
    with patch("cli.analyze_commit_quality.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=diff_with_todo, stderr="")
        args = argparse.Namespace(
            commits=None, diff=None, format="json",
            checks=["quality"]
        )
        result = quality_script.execute(args)
    violations = result.get("violations", result.get("issues", []))
    assert len(violations) > 0 or result.get("total_violations", 0) > 0

# ---------------------------------------------------------------------------
# Integration: format + validate pipeline
# ---------------------------------------------------------------------------

def test_format_then_validate_pipeline(format_script):
    import argparse

    # Step 1: format a message
    format_args = argparse.Namespace(
        validate=False, suggest=False,
        issue="#7", type="fix",
        message="resolve null pointer in UserService",
        format="json"
    )
    format_result = format_script.execute(format_args)
    formatted = format_result.get("formatted", "")
    assert formatted != ""

    # Step 2: validate the formatted message
    validate_args = argparse.Namespace(
        validate=True, suggest=False, issue=None, type=None,
        message=formatted, format="json"
    )
    validate_result = format_script.execute(validate_args)
    assert validate_result["valid"] is True
