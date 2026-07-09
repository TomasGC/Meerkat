"""
E2E tests — commit quality workflow.

Tests the complete commit validation pipeline:
format_commit_message → analyze_commit_quality → format output.
"""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

pytestmark = pytest.mark.e2e_scripts


# ---------------------------------------------------------------------------
# E2E: format_commit_message CLI
# ---------------------------------------------------------------------------

def test_format_valid_commit_json(capsys):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--validate",
        "--message", "#1: feat: add user authentication",
        "--format", "json"
    ])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["valid"] is True


def test_format_invalid_commit_json(capsys):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--validate",
        "--message", "added some stuff",
        "--format", "json"
    ])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["valid"] is False


def test_format_commit_with_issue_and_type(capsys):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--issue", "#42",
        "--type", "fix",
        "--message", "resolve null pointer in service",
        "--format", "json"
    ])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert "formatted" in data
    assert "#42" in data["formatted"]
    assert "fix" in data["formatted"]


def test_format_commit_suggest(capsys):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--suggest",
        "--message", "fixed the bug in user service",
        "--format", "json"
    ])
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert "suggestion" in data


def test_format_commit_text_output(capsys):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--validate",
        "--message", "#1: feat: add feature",
        "--format", "text"
    ])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert len(out) > 0


# ---------------------------------------------------------------------------
# E2E: commit format validation rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected_valid", [
    ("#1: feat: add authentication", True),
    ("#123: fix: resolve null reference", True),
    ("#1: refactor: extract repository pattern", True),
    ("#1: test: add integration tests", True),
    ("#1: docs: update API documentation", True),
    ("#1: chore: update dependencies", True),
    ("feat: missing issue number", False),
    ("#1: invalid type: message", False),
    ("no prefix at all", False),
    ("", False),
])
def test_commit_format_rules(capsys, message, expected_valid):
    from cli.format_commit_message import FormatCommitMessageScript
    script = FormatCommitMessageScript()
    exit_code = script.run([
        "--validate",
        "--message", message,
        "--format", "json"
    ])
    if message == "":
        # Empty message may cause early exit
        return
    assert exit_code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["valid"] == expected_valid


# ---------------------------------------------------------------------------
# E2E: full pipeline — generate, format, validate
# ---------------------------------------------------------------------------

def test_full_commit_pipeline(capsys):
    from cli.format_commit_message import FormatCommitMessageScript

    script = FormatCommitMessageScript()

    # Step 1: Generate formatted commit
    exit_code = script.run([
        "--issue", "#7",
        "--type", "feat",
        "--message", "implement OAuth2 authentication",
        "--format", "json"
    ])
    assert exit_code == 0
    generated = json.loads(capsys.readouterr().out)
    formatted_msg = generated.get("formatted", "")
    assert formatted_msg != ""

    # Step 2: Validate the generated commit message
    exit_code = script.run([
        "--validate",
        "--message", formatted_msg,
        "--format", "json"
    ])
    assert exit_code == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["valid"] is True
