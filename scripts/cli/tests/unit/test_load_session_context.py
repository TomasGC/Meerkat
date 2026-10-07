#!/usr/bin/env python3
"""Tests for load_session_context.py"""

import argparse
from unittest.mock import patch

import pytest

from cli.load_session_context import LoadSessionContextScript, load_kanban_entry, load_session_context

KANBAN = """# KANBAN

---

2026-10-07 - [#35] Fix the session loader
- Kanban found inside the repository only
tag: #skills
Commit: abc1234

2026-10-06 - [#2] Run the suites on GitHub Actions
- Workflows call Condor
Commit: def5678
"""


@pytest.fixture
def repo(tmp_path):
    """A repository whose kanban has entries for #35 and #2."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    kanban = tmp_path / ".claude" / "contexts" / "kanban.md"
    kanban.parent.mkdir(parents=True)
    kanban.write_text(KANBAN, encoding="utf-8")
    return tmp_path


@pytest.fixture
def on_branch():
    """Pretend git is on feature/35-session-loader, with branch-derived issues formatted as #N."""
    with (
        patch("cli.load_session_context.run_command", return_value=(0, "feature/35-session-loader\n", "")),
        patch("cli.load_session_context.get_issue_format", return_value=r"#\d+"),
    ):
        yield


def test_load_kanban_entry_returns_the_issue_entry_only(repo):
    entry = load_kanban_entry("#35", repo / ".claude" / "contexts" / "kanban.md")
    assert entry.startswith("[#35] Fix the session loader")
    assert "Commit: abc1234" in entry
    assert "#2]" not in entry


def test_load_kanban_entry_without_the_issue_is_none(repo):
    assert load_kanban_entry("#99", repo / ".claude" / "contexts" / "kanban.md") is None


@pytest.mark.usefixtures("on_branch")
def test_session_context_finds_the_repository_kanban(repo):
    context = load_session_context(cwd=repo)
    assert context["issue"] == "#35"
    assert context["kanbanFound"] is True
    assert context["kanbanFile"] == str(repo / ".claude" / "contexts" / "kanban.md")


@pytest.mark.usefixtures("on_branch")
def test_explicit_kanban_file_is_used(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kanban = tmp_path / "elsewhere.md"
    kanban.write_text(KANBAN, encoding="utf-8")
    result = LoadSessionContextScript().execute(argparse.Namespace(kanban_file=str(kanban)))
    assert result["success"] is True
    assert result["kanbanFound"] is True
    assert result["kanbanFile"] == str(kanban)


@pytest.mark.usefixtures("on_branch")
def test_missing_explicit_kanban_file_is_an_error(tmp_path):
    result = LoadSessionContextScript().execute(argparse.Namespace(kanban_file=str(tmp_path / "none.md")))
    assert result["success"] is False
    assert "kanban.md not found at" in result["error"]


@pytest.mark.usefixtures("on_branch")
def test_no_kanban_in_the_repository_is_reported_in_text(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    script = LoadSessionContextScript()
    result = script.execute(argparse.Namespace(kanban_file=""))
    assert result["kanbanFile"] is None
    assert "kanban.md not found in this repository" in script.format_text(result)


def test_kanban_file_argument_parses():
    args = LoadSessionContextScript().create_parser().parse_args(["--kanban-file", "k.md", "--format", "text"])
    assert args.kanban_file == "k.md"
    assert args.format == "text"
