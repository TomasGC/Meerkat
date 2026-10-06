#!/usr/bin/env python3
"""Tests for get_commit_info.py"""

import argparse
import csv
import io
import json
from unittest.mock import patch

import pytest

from cli.get_commit_info import GetCommitInfoScript, format_csv_output, get_commit_files, get_commit_info


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


# ── run_command mocked ────────────────────────────────────────────────────────

HASH = "c" * 40
LOG_BLOCK = f"{HASH}\nccccccc\nfeat: add parser\nAda\nada@example.com\n2026-01-01 10:00:00 +0000\n2 days ago"
NUMSTAT = "5\t2\tsrc/parser.py\n-\t-\tlogo.png\n\nmalformed\n"


def _git(cmd, **_kwargs):
    if cmd[:2] == ["git", "log"]:
        return 0, LOG_BLOCK + "\n" + LOG_BLOCK.replace("feat: add parser", "fix: edge case") + "\n", ""
    if cmd[:2] == ["git", "show"]:
        return 0, NUMSTAT, ""
    return 1, "", "unexpected"


def _execute(**kwargs):
    args = argparse.Namespace(**{"hash": "HEAD", "count": 2, "include_files": False, "format_csv": False, **kwargs})
    with patch("cli.get_commit_info.run_command", side_effect=_git):
        return GetCommitInfoScript().execute(args)


def test_get_commit_info_parses_seven_line_blocks():
    with patch("cli.get_commit_info.run_command", side_effect=_git):
        commits = get_commit_info("HEAD", count=2, include_files=True)

    assert [c.message for c in commits] == ["feat: add parser", "fix: edge case"]
    first = commits[0]
    assert (first.hash, first.author, first.date) == (HASH, "Ada", "2026-01-01 10:00:00 +0000")
    assert first.files_changed == ["src/parser.py", "logo.png"]
    assert (first.insertions, first.deletions) == (5, 2)


def test_get_commit_info_ignores_incomplete_block():
    with patch("cli.get_commit_info.run_command", return_value=(0, "abc\nshort\n", "")):
        assert get_commit_info() == []


def test_execute_without_commits_is_an_error():
    with patch("cli.get_commit_info.run_command", return_value=(0, "", "")):
        result = GetCommitInfoScript().execute(
            argparse.Namespace(hash="HEAD", count=1, include_files=False, format_csv=False)
        )
    assert result == {"success": False, "error": "No commits found"}


def test_execute_git_failure_is_reported():
    with patch("cli.get_commit_info.run_command", return_value=(128, "", "bad revision")):
        result = GetCommitInfoScript().execute(
            argparse.Namespace(hash="nope", count=1, include_files=False, format_csv=False)
        )
    assert result == {"success": False, "error": "Git log failed: bad revision"}


def test_format_text_output_with_files():
    text = GetCommitInfoScript().format_text(_execute(include_files=True))
    assert text.startswith(f"Commit:  {HASH}\nAuthor:  Ada\n")
    assert "Message: feat: add parser" in text
    assert "Files:   2 changed, +5 insertions, -2 deletions\n  - src/parser.py\n  - logo.png" in text
    assert "\n\nCommit:  " in text  # blank line between commits


def test_format_summary_single_and_many():
    script = GetCommitInfoScript()
    result = _execute()
    assert script.format_summary(result) == "2 commits retrieved"
    result["commits"] = result["commits"][:1]
    assert script.format_summary(result) == "ccccccc - feat: add parser"


def test_error_result_formats():
    script = GetCommitInfoScript()
    assert script.format_text({"success": False, "error": "x"}) == "Error: x"
    assert script.format_summary({"success": False, "error": "x"}) == "[ERROR] x"


def test_format_csv_output_with_and_without_files():
    commits = _execute(include_files=True)["commits"]

    rows = list(csv.DictReader(io.StringIO(format_csv_output(commits, include_files=True))))
    assert rows[0] == {
        "hash": HASH,
        "author": "Ada",
        "date": "2026-01-01 10:00:00 +0000",
        "message": "feat: add parser",
        "files": "src/parser.py;logo.png",
        "insertions": "5",
        "deletions": "2",
    }
    header = format_csv_output(commits, include_files=False).splitlines()[0]
    assert header == "hash,author,date,message"


def test_run_csv_flag_prints_csv(capsys):
    with patch("cli.get_commit_info.run_command", side_effect=_git):
        assert GetCommitInfoScript().run(["--count", "2", "--format-csv"]) == 0
    assert capsys.readouterr().out.startswith("hash,author,date,message")


def test_run_text_format(capsys):
    with patch("cli.get_commit_info.run_command", side_effect=_git):
        GetCommitInfoScript().run(["--format", "summary"])
    assert capsys.readouterr().out.strip() == "2 commits retrieved"


@pytest.mark.xfail(
    strict=True,
    reason="bug (#51): execute() returns GitCommitInfo dataclasses, so the default --format json cannot serialize them",
)
def test_run_default_json_format_succeeds(capsys):
    with patch("cli.get_commit_info.run_command", side_effect=_git):
        assert GetCommitInfoScript().run([]) == 0
    assert json.loads(capsys.readouterr().out)["success"] is True
