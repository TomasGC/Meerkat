"""Integration (mocked git): update_kanban.py writes a real kanban.md in tmp_path."""

import argparse
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.search_kanban import KanbanEntry
from cli.update_kanban import UpdateKanbanScript, get_commit_title, update_existing_entry

KANBAN = """\
# KANBAN - Test

---

2026-05-01 - [#1] Add authentication
- Implemented JWT token validation
tags: #auth
Commit: abc123f

---

## Notes
"""

TODAY = datetime.now().strftime("%Y-%m-%d")

_GIT = {
    ("git", "branch", "--show-current"): (0, "feature/#7-x\n", ""),
    ("git", "merge-base", "main", "feature/#7-x"): (0, "base\n", ""),
    ("git", "rev-list", "base..feature/#7-x"): (0, "1234567890\n", ""),
    ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "1234567"): (0, "tests/test_a.py\nsrc/a.py\n", ""),
    ("git", "log", "-1", "--format=%s", "1234567"): (0, "#7: feat: add the a module\n", ""),
}


def _git(cmd, **_kwargs):
    return _GIT.get(tuple(cmd), (1, "", "fail"))


@pytest.fixture
def git():
    """Every run_command the update pipeline reaches, answered from _GIT."""
    with patch("cli.update_kanban.run_command", side_effect=_git), patch(
        "cli.generate_comment.run_command", side_effect=_git
    ):
        yield


@pytest.fixture
def kanban(tmp_path):
    path = tmp_path / ".claude" / "contexts" / "kanban.md"
    path.parent.mkdir(parents=True)
    path.write_text(KANBAN, encoding="utf-8")
    return path


def _args(**kwargs):
    defaults = dict(issue="", commits="", description="", ref="", kanban_file="", no_backup=True, auto=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.mark.usefixtures("git")
def test_get_commit_title_strips_type_prefix():
    assert get_commit_title("1234567") == "feat: add the a module"


def test_get_commit_title_without_prefix_or_on_failure():
    with patch("cli.update_kanban.run_command", return_value=(0, "plain title\n", "")):
        assert get_commit_title("x") == "plain title"
    with patch("cli.update_kanban.run_command", return_value=(1, "", "")):
        assert get_commit_title("x") == ""


@pytest.mark.usefixtures("git")
def test_auto_mode_creates_entry_from_branch_commits(kanban, monkeypatch):
    monkeypatch.chdir(kanban.parent.parent.parent)
    with patch("cli.update_kanban.extract_issue", return_value="#7"):
        result = UpdateKanbanScript().execute(_args(auto=True, ref="https://x.test/7"))

    assert result == {
        "success": True,
        "issue": "#7",
        "action": "created",
        "commits": 1,
        "kanban_file": str(kanban),
        "backup": None,
    }
    content = kanban.read_text(encoding="utf-8")
    assert f"{TODAY} - [#7] feat: add the a module" in content
    assert "Ref: https://x.test/7" in content
    assert "Commit: 1234567" in content
    assert content.index("[#7]") < content.index("[#1]")


@pytest.mark.usefixtures("git")
def test_existing_entry_is_updated_in_place_with_backup(kanban):
    result = UpdateKanbanScript().execute(
        _args(
            issue="#1",
            commits="new789a",
            description="- Added refresh tokens",
            kanban_file=str(kanban),
            no_backup=False,
        )
    )

    assert result["action"] == "updated"
    backup = Path(result["backup"])
    assert backup.parent == kanban.parent
    assert backup.name.startswith("kanban.backup-") and backup.suffix == ".md"
    assert backup.read_text(encoding="utf-8") == KANBAN
    content = kanban.read_text(encoding="utf-8")
    assert f"{TODAY} - [#1] Add authentication" in content
    assert "- Added refresh tokens" in content
    assert "Commits: abc123f, new789a" in content


@pytest.mark.usefixtures("git")
def test_new_entry_without_commits_uses_issue_as_title(kanban):
    UpdateKanbanScript().execute(_args(issue="#9", kanban_file=str(kanban)))
    content = kanban.read_text(encoding="utf-8")
    assert f"{TODAY} - [#9] #9\n- Work completed" in content


@pytest.mark.usefixtures("git")
def test_new_entry_title_falls_back_to_issue_when_commit_unreadable(kanban):
    UpdateKanbanScript().execute(_args(issue="#9", commits="ffffff0", description="- x", kanban_file=str(kanban)))
    assert f"{TODAY} - [#9] #9" in kanban.read_text(encoding="utf-8")


def test_undetectable_issue_is_an_error(kanban):
    with patch("cli.update_kanban.extract_issue", return_value=None):
        result = UpdateKanbanScript().execute(_args())
    assert result == {"success": False, "error": "Could not detect issue ID. Please provide --issue parameter."}


@pytest.mark.usefixtures("git")
def test_missing_explicit_kanban_file_is_an_error(tmp_path):
    result = UpdateKanbanScript().execute(_args(issue="#1", kanban_file=str(tmp_path / "none.md")))
    assert result["success"] is False
    assert "kanban.md not found at" in result["error"]


@pytest.mark.usefixtures("git")
def test_no_kanban_found_from_cwd_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("cli.update_kanban.find_kanban_file", return_value=None):
        result = UpdateKanbanScript().execute(_args(issue="#1"))
    assert "not found in this repository" in result["error"]


def test_auto_mode_outside_a_branch_records_no_commits(kanban):
    with patch("cli.update_kanban.run_command", return_value=(128, "", "")):
        result = UpdateKanbanScript().execute(_args(issue="#5", auto=True, kanban_file=str(kanban)))
    assert result["commits"] == 0


def test_update_existing_entry_keeps_several_refs():
    existing = KanbanEntry(date="2026-01-01", issue_id="#1", title="T", refs=["https://a", "https://b"], commits=["c1"])
    updated = update_existing_entry(existing, "", [])
    assert "Refs:\n- https://a\n- https://b\nCommit: c1" in updated


def test_text_and_summary_formats():
    script = UpdateKanbanScript()
    result = {"success": True, "issue": "#1", "action": "updated", "commits": 2, "kanban_file": "k.md", "backup": "b"}
    assert script.format_text(result) == "Updated entry for [#1]\nCommits: 2\nKANBAN: k.md\nBackup: b"
    assert script.format_summary({**result, "action": "created"}) == "[OK] Created [#1] (2 commits)"
    assert script.format_text({"success": False, "error": "x"}) == "Error: x"
    assert script.format_summary({"success": False, "error": "x"}) == "[ERROR] x"
