#!/usr/bin/env python3
"""Tests for get_branch_summary.py"""

import argparse
import json
from unittest.mock import patch

import pytest
from cli.get_branch_summary import (
    GetBranchSummaryScript,
    format_brief_summary,
    format_markdown_summary,
    format_text_summary,
    get_branch_commits,
    get_commit_file_stats,
    get_current_branch,
    get_default_base_branch,
    get_uncommitted_changes,
)


def test_get_default_base_branch_main():
    """Test detecting main as default branch."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        # Mock: origin remote exists
        mock_run.side_effect = [
            (0, "origin\n", ""),  # git remote
            (1, "", ""),  # git symbolic-ref (fails)
            (0, "origin/main\norigin/feature\n", ""),  # git branch -r
        ]

        result = get_default_base_branch()
        assert result == "main"


def test_get_default_base_branch_master():
    """Test detecting master as default branch."""
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.side_effect = [(0, "origin\n", ""), (1, "", ""), (0, "origin/master\norigin/feature\n", "")]

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


# ── helpers ───────────────────────────────────────────────────────────────────

H1 = "a" * 40
H2 = "b" * 40


def _fake_git(responses):
    """run_command stand-in: answers each git command from `responses`, else fails."""

    def run(cmd, **_kwargs):
        return responses.get(tuple(cmd), (1, "", "unknown command"))

    return run


def _branch_repo(**overrides):
    """Answers for a feature branch two commits ahead of main, with one file of each change kind."""
    responses = {
        ("git", "branch", "--show-current"): (0, "feature/x\n", ""),
        ("git", "remote"): (0, "origin\n", ""),
        ("git", "symbolic-ref", "refs/remotes/origin/HEAD"): (0, "refs/remotes/origin/main\n", ""),
        ("git", "log", "--format=%H", "main..feature/x"): (0, f"{H1}\n{H2}\n", ""),
        ("git", "log", "-1", "--format=%s%n%an%n%ai", H1): (0, "feat: one\nAda\n2026-01-01 10:00:00\n", ""),
        ("git", "log", "-1", "--format=%s%n%an%n%ai", H2): (0, "fix: two\nBob\n2026-01-02 10:00:00\n", ""),
        ("git", "show", "--numstat", "--format=", H1): (0, "3\t1\tsrc/a.py\n-\t-\tlogo.png\n", ""),
        ("git", "show", "--numstat", "--format=", H2): (0, "2\t0\tsrc/a.py\n", ""),
        ("git", "diff", "--cached", "--name-status"): (0, "A\tnew.py\n", ""),
        ("git", "diff", "--name-status"): (0, "M\tsrc/a.py\n", ""),
        ("git", "ls-files", "--others", "--exclude-standard"): (0, "notes.txt\n", ""),
    }
    responses.update(overrides)
    return _fake_git(responses)


def _args(base_branch="", no_uncommitted=False):
    return argparse.Namespace(base_branch=base_branch, no_uncommitted=no_uncommitted, format_markdown=False)


def _summary():
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        return GetBranchSummaryScript().execute(_args())["summary"]


# ── base branch detection ─────────────────────────────────────────────────────


def test_get_default_base_branch_reads_remote_head():
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        assert get_default_base_branch() == "main"


def test_get_default_base_branch_develop():
    with patch("cli.get_branch_summary.run_command") as mock_run:
        mock_run.side_effect = [(0, "", ""), (0, "origin/develop\n", "")]
        assert get_default_base_branch() == "develop"


# ── commits and file stats ────────────────────────────────────────────────────


def test_get_branch_commits_collects_metadata_and_stats():
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        commits = get_branch_commits("main", "feature/x")

    assert [c.message for c in commits] == ["feat: one", "fix: two"]
    first = commits[0]
    assert (first.short_hash, first.author, first.date) == ("aaaaaaa", "Ada", "2026-01-01 10:00:00")
    assert (first.additions, first.deletions, first.files_changed) == (3, 1, 2)
    assert first.files[1].path == "logo.png" and first.files[1].additions == 0  # binary file


def test_get_branch_commits_falls_back_to_origin_prefix():
    run = _fake_git(
        {
            ("git", "log", "--format=%H", "origin/main..feature/x"): (0, f"{H2}\n", ""),
            ("git", "log", "-1", "--format=%s%n%an%n%ai", H2): (0, "fix: two\nBob\n2026-01-02\n", ""),
            ("git", "show", "--numstat", "--format=", H2): (0, "2\t0\tsrc/a.py\n", ""),
        }
    )
    with patch("cli.get_branch_summary.run_command", side_effect=run):
        commits = get_branch_commits("main", "feature/x")
    assert [c.hash for c in commits] == [H2]


def test_get_branch_commits_empty_when_no_range_resolves():
    with patch("cli.get_branch_summary.run_command", return_value=(128, "", "bad")):
        assert get_branch_commits("main", "feature/x") == []


def test_get_branch_commits_skips_unreadable_or_truncated_commits():
    run = _fake_git(
        {
            ("git", "log", "--format=%H", "main..feature/x"): (0, f"{H1}\n{H2}\n", ""),
            ("git", "log", "-1", "--format=%s%n%an%n%ai", H2): (0, "only subject\n", ""),
        }
    )
    with patch("cli.get_branch_summary.run_command", side_effect=run):
        assert get_branch_commits("main", "feature/x") == []


def test_get_commit_file_stats_ignores_malformed_lines():
    with patch("cli.get_branch_summary.run_command", return_value=(0, "\nonly-one-field\n4\t2\tx.py\n", "")):
        files, added, deleted = get_commit_file_stats(H1)
    assert [f.path for f in files] == ["x.py"]
    assert (added, deleted) == (4, 2)


def test_get_commit_file_stats_empty_on_git_failure():
    with patch("cli.get_branch_summary.run_command", return_value=(1, "", "")):
        assert get_commit_file_stats(H1) == ([], 0, 0)


def test_get_uncommitted_changes_splits_staged_unstaged_untracked():
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        changes = get_uncommitted_changes()

    assert [(f.status, f.path) for f in changes.staged] == [("A", "new.py")]
    assert [(f.status, f.path) for f in changes.unstaged] == [("M", "src/a.py")]
    assert [(f.status, f.path) for f in changes.untracked] == [("?", "notes.txt")]


# ── script ────────────────────────────────────────────────────────────────────


def test_execute_totals_commits_and_unique_files():
    summary = _summary()

    assert summary.current_branch == "feature/x"
    assert summary.base_branch == "main"
    assert summary.commits_count == 2
    assert (summary.total_additions, summary.total_deletions) == (5, 1)
    assert summary.unique_files_changed == 2  # src/a.py counted once
    assert summary.has_uncommitted_changes is True


def test_execute_no_uncommitted_skips_working_tree():
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        result = GetBranchSummaryScript().execute(_args(base_branch="main", no_uncommitted=True))
    assert result["summary"].has_uncommitted_changes is False


def test_execute_outside_a_branch_reports_error():
    with patch("cli.get_branch_summary.run_command", return_value=(1, "", "fatal")):
        result = GetBranchSummaryScript().execute(_args())
    assert result["success"] is False
    assert "git repository" in result["error"]


def test_format_text_summary_lists_commits_and_changes():
    text = format_text_summary(_summary())

    assert "Current branch: feature/x" in text
    assert "Lines: +5 -1" in text
    assert "aaaaaaa - feat: one" in text
    assert "Staged (1):" in text and "  A new.py" in text
    assert "Unstaged (1):" in text
    assert "Untracked (1):" in text and "  ? notes.txt" in text


def test_format_markdown_summary_has_sections():
    md = format_markdown_summary(_summary())

    assert md.startswith("# Branch Summary: feature/x")
    assert "### aaaaaaa - feat: one" in md
    assert "### Staged (1)" in md and "- `A` new.py" in md
    assert "### Unstaged (1)" in md
    assert "### Untracked (1)" in md and "- `?` notes.txt" in md


def test_format_brief_summary():
    assert format_brief_summary(_summary()) == "2 commits, 2 files changed (+5 -1)"


def test_run_text_format_prints_text_summary(capsys):
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        code = GetBranchSummaryScript().run(["--format", "text"])
    assert code == 0
    assert "Branch Summary" in capsys.readouterr().out


def test_run_summary_format_prints_one_line(capsys):
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        GetBranchSummaryScript().run(["--format", "summary"])
    assert capsys.readouterr().out.strip() == "2 commits, 2 files changed (+5 -1)"


def test_run_format_markdown_flag_prints_markdown(capsys):
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        GetBranchSummaryScript().run(["--format-markdown"])
    assert capsys.readouterr().out.startswith("# Branch Summary: feature/x")


def test_error_result_formats():
    script = GetBranchSummaryScript()
    assert script.format_text({"success": False, "error": "x"}) == "Error: x"
    assert script.format_summary({"success": False, "error": "x"}) == "[ERROR] x"


@pytest.mark.xfail(
    strict=True,
    reason="bug (#51): execute() returns a BranchSummary dataclass, so the default --format json cannot serialize it",
)
def test_run_default_json_format_succeeds(capsys):
    with patch("cli.get_branch_summary.run_command", side_effect=_branch_repo()):
        code = GetBranchSummaryScript().run([])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["success"] is True
