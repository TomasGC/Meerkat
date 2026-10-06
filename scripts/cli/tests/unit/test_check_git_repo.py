#!/usr/bin/env python3
"""Tests for check_git_repo.py (run_command mocked)."""

import argparse
import json
from unittest.mock import patch

import pytest

from cli.check_git_repo import CheckGitRepoScript


def _git(responses):
    def run(cmd, **_kwargs):
        return responses.get(tuple(cmd), (1, "", "fail"))

    return run


_REPO = {
    ("git", "rev-parse", "--git-dir"): (0, ".git\n", ""),
    ("git", "branch", "--show-current"): (0, "main\n", ""),
    ("git", "remote"): (0, "origin\nupstream\n", ""),
    ("git", "remote", "get-url", "origin"): (0, "https://github.com/o/r.git\n", ""),
    ("git", "status", "--porcelain"): (0, " M a.py\n?? b.py\n", ""),
}


def _execute(tmp_path, responses, info=True):
    with patch("cli.check_git_repo.run_command", side_effect=_git(responses)):
        return CheckGitRepoScript().execute(argparse.Namespace(path=tmp_path, info=info))


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Path not found"):
        CheckGitRepoScript().execute(argparse.Namespace(path=tmp_path / "absent", info=False))


def test_info_reports_branch_remote_and_status(tmp_path):
    result = _execute(tmp_path, _REPO)
    assert result == {
        "isRepo": True,
        "path": str(tmp_path.resolve()),
        "branch": "main",
        "hasRemote": True,
        "remote": "origin",
        "remoteUrl": "https://github.com/o/r.git",
        "hasUncommittedChanges": True,
        "statusLines": 2,
    }


def test_info_without_remote_and_clean_tree(tmp_path):
    responses = {**_REPO, ("git", "remote"): (0, "", ""), ("git", "status", "--porcelain"): (0, "", "")}
    result = _execute(tmp_path, responses)
    assert result["hasRemote"] is False
    assert (result["hasUncommittedChanges"], result["statusLines"]) == (False, 0)


def test_info_remote_without_url_and_failed_status(tmp_path):
    responses = dict(_REPO)
    del responses[("git", "remote", "get-url", "origin")]
    del responses[("git", "status", "--porcelain")]
    responses[("git", "branch", "--show-current")] = (0, "\n", "")  # detached HEAD
    result = _execute(tmp_path, responses)
    assert result["branch"] is None
    assert result["hasRemote"] is False
    assert result["hasUncommittedChanges"] is None


def test_non_repo_skips_info(tmp_path):
    result = _execute(tmp_path, {})
    assert result == {"isRepo": False, "path": str(tmp_path.resolve())}


def test_format_text_full_repo(tmp_path):
    text = CheckGitRepoScript().format_text(_execute(tmp_path, _REPO))
    assert text.splitlines()[1:] == [
        "Status: Git repository",
        "Branch: main",
        "Remote: origin",
        "URL: https://github.com/o/r.git",
        "Uncommitted: Yes (2 files)",
    ]


def test_format_text_clean_repo_without_remote():
    result = {"isRepo": True, "path": "p", "branch": "dev", "hasRemote": False, "hasUncommittedChanges": False}
    assert CheckGitRepoScript().format_text(result) == (
        "Path: p\nStatus: Git repository\nBranch: dev\nRemote: None\nUncommitted: No"
    )


def test_format_text_not_a_repo():
    assert CheckGitRepoScript().format_text({"isRepo": False, "path": "p"}) == "Path: p\nStatus: Not a git repository"


def test_format_summary():
    script = CheckGitRepoScript()
    assert script.format_summary({"isRepo": True, "branch": "main"}) == "Git repo: main"
    assert script.format_summary({"isRepo": True}) == "Git repo: unknown"
    assert script.format_summary({"isRepo": False}) == "Not a git repo"


def test_run_prints_json(tmp_path, capsys):
    with patch("cli.check_git_repo.run_command", side_effect=_git(_REPO)):
        assert CheckGitRepoScript().run(["--path", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"isRepo": True, "path": str(tmp_path.resolve())}
