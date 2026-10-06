#!/usr/bin/env python3
"""Tests for search_github module (gh CLI mocked at subprocess.run and shutil.which)."""

import json
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

import search_github
from search_github import check_gh_cli, search_github_discussions, search_github_issues
from search_tech.logger import MetricsCollector
from search_tech.models import ResultType, SearchQuery, SearchResult, Source

ISSUES = [
    {
        "title": "Memory leak in worker",
        "url": "https://github.com/o/r/issues/1",
        "state": "open",
        "comments": 4,
        "createdAt": "2026-01-02T03:04:05Z",
        "reactions": {"+1": 5, "hooray": 1, "heart": 2},
        "repository": {"nameWithOwner": "o/r"},
        "body": "y" * 250,
    },
    {"title": "No body", "url": "https://github.com/o/r/issues/2", "repository": {"nameWithOwner": "o/r"}},
]

DISCUSSIONS = {
    "data": {
        "search": {
            "nodes": [
                {
                    "title": "How to avoid leaks?",
                    "url": "https://github.com/o/r/discussions/3",
                    "createdAt": "2026-02-01T00:00:00Z",
                    "upvoteCount": 9,
                    "comments": {"totalCount": 2},
                    "repository": {"nameWithOwner": "o/r"},
                    "body": "short body",
                },
                None,
                {
                    "title": "Empty",
                    "url": "https://github.com/o/r/discussions/4",
                    "repository": {"nameWithOwner": "o/r"},
                    "category": {"name": "Q&A"},
                },
            ]
        }
    }
}


def _done(stdout="", returncode=0, stderr=""):
    return Mock(returncode=returncode, stdout=stdout, stderr=stderr)


def _gh(issues=ISSUES, discussions=DISCUSSIONS):
    """subprocess.run stand-in for an authenticated gh answering both searches."""

    def run(cmd, **_kwargs):
        if cmd[:3] == ["gh", "auth", "status"]:
            return _done()
        if cmd[:3] == ["gh", "search", "issues"]:
            return _done(json.dumps(issues))
        if cmd[:3] == ["gh", "api", "graphql"]:
            return _done(json.dumps(discussions))
        raise AssertionError(f"unexpected command {cmd}")

    return run


@pytest.fixture(autouse=True)
def gh_installed():
    with patch("search_github.shutil.which", return_value="/usr/bin/gh"), patch("search_github.time.sleep"):
        yield


# ── check_gh_cli ──────────────────────────────────────────────────────────────


def test_check_gh_cli_not_installed():
    with patch("search_github.shutil.which", return_value=None):
        assert check_gh_cli() == (False, "gh CLI not found. Install from https://cli.github.com/")


@pytest.mark.parametrize(
    "outcome,expected",
    [
        (_done(), (True, "")),
        (_done(returncode=1), (False, "gh CLI not authenticated. Run: gh auth login")),
        (subprocess.TimeoutExpired("gh", 5), (False, "gh CLI authentication check timeout")),
        (OSError("denied"), (False, "gh CLI check error: denied")),
    ],
)
def test_check_gh_cli_auth_states(outcome, expected):
    kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
    with patch("search_github.subprocess.run", **kwargs):
        assert check_gh_cli() == expected


# ── issues ────────────────────────────────────────────────────────────────────


def test_search_issues_converts_results():
    with patch("search_github.subprocess.run", side_effect=_gh()) as run:
        results = search_github_issues(SearchQuery(keywords=["memory", "leak"], language="go"))

    search_cmd = run.call_args_list[-1][0][0]
    assert search_cmd[3] == "memory leak language:go sort:reactions-+1"
    first, second = results
    assert (first.source, first.result_type) == (Source.GITHUB_ISSUE, ResultType.ISSUE)
    assert first.score == 8
    assert first.excerpt == "y" * 200 + "..."
    assert (first.comments, first.status, first.repository) == (4, "open", "o/r")
    assert first.created_date.year == 2026
    assert second.excerpt == "Issue in o/r"
    assert (second.status, second.created_date) == ("unknown", None)


def test_search_issues_without_gh_returns_nothing():
    with patch("search_github.shutil.which", return_value=None):
        assert search_github_issues(SearchQuery(keywords=["x"])) == []


def test_search_issues_retries_failed_calls_then_gives_up():
    metrics = MetricsCollector()

    def run(cmd, **_kwargs):
        return _done() if cmd[1] == "auth" else _done(returncode=1, stderr="rate limited")

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_issues(SearchQuery(keywords=["x"]), metrics=metrics, max_retries=2) == []
    assert (metrics.get("api_calls"), metrics.get("errors"), metrics.get("retries")) == (2, 2, 1)


def test_search_issues_timeout_then_success():
    answers = iter([subprocess.TimeoutExpired("gh", 10), _done(json.dumps(ISSUES[:1]))])

    def run(cmd, **_kwargs):
        if cmd[1] == "auth":
            return _done()
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    with patch("search_github.subprocess.run", side_effect=run):
        results = search_github_issues(SearchQuery(keywords=["x"]), max_retries=2)
    assert [r.title for r in results] == ["Memory leak in worker"]


def test_search_issues_all_timeouts_return_empty():
    def run(cmd, **_kwargs):
        if cmd[1] == "auth":
            return _done()
        raise subprocess.TimeoutExpired("gh", 10)

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_issues(SearchQuery(keywords=["x"]), max_retries=2) == []


@pytest.mark.parametrize("stdout", ["not json", "[1]"])
def test_search_issues_bad_payload_returns_empty(stdout):
    def run(cmd, **_kwargs):
        return _done() if cmd[1] == "auth" else _done(stdout)

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_issues(SearchQuery(keywords=["x"])) == []


# ── discussions ───────────────────────────────────────────────────────────────


def test_search_discussions_converts_results_and_skips_null_nodes():
    with patch("search_github.subprocess.run", side_effect=_gh()):
        results = search_github_discussions(SearchQuery(keywords=["leak"], language="rust"))

    assert [r.title for r in results] == ["How to avoid leaks?", "Empty"]
    first, second = results
    assert (first.source, first.result_type) == (Source.GITHUB_DISCUSSION, ResultType.DISCUSSION)
    assert (first.score, first.comments, first.excerpt) == (9, 2, "short body")
    assert second.excerpt == "Discussion in o/r (Q&A)"
    assert second.created_date is None


def test_search_discussions_without_gh_returns_nothing():
    with patch("search_github.shutil.which", return_value=None):
        assert search_github_discussions(SearchQuery(keywords=["x"])) == []


def test_search_discussions_failed_call_returns_empty():
    def run(cmd, **_kwargs):
        return _done() if cmd[1] == "auth" else _done(returncode=1)

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_discussions(SearchQuery(keywords=["x"]), max_retries=2) == []


def test_search_discussions_timeouts_return_empty():
    def run(cmd, **_kwargs):
        if cmd[1] == "auth":
            return _done()
        raise subprocess.TimeoutExpired("gh", 10)

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_discussions(SearchQuery(keywords=["x"]), max_retries=2) == []


@pytest.mark.parametrize("stdout", ["not json", '{"data": {"search": {"nodes": [1]}}}'])
def test_search_discussions_bad_payload_returns_empty(stdout):
    def run(cmd, **_kwargs):
        return _done() if cmd[1] == "auth" else _done(stdout)

    with patch("search_github.subprocess.run", side_effect=run):
        assert search_github_discussions(SearchQuery(keywords=["x"])) == []


# ── main ──────────────────────────────────────────────────────────────────────


def _main(argv, tmp_path, cache=None):
    out = tmp_path / "gh.json"
    with patch.object(sys, "argv", ["search_github.py", *argv, "--output", str(out)]), patch(
        "search_github.SearchCache", return_value=cache
    ):
        search_github.main()
    return json.loads(out.read_text(encoding="utf-8"))


def test_main_searches_both_kinds_and_caches(tmp_path):
    cache = Mock()
    cache.get.return_value = None
    with patch("search_github.subprocess.run", side_effect=_gh()):
        data = _main(["memory leak", "--verbose"], tmp_path, cache=cache)

    assert data["success"] is True
    assert len(data["results"]) == 4
    cache.set.assert_called_once()
    assert cache.set.call_args[0][0] == "memory leak"


def test_main_cache_hit_skips_searches(tmp_path):
    cached = SearchResult(
        source=Source.GITHUB_ISSUE, result_type=ResultType.ISSUE, title="Cached", url="u", score=1, excerpt="e"
    )
    cache = Mock()
    cache.get.return_value = {"results": [cached.to_dict()]}

    def run(cmd, **_kwargs):
        assert cmd[1] == "auth", "a cache hit must not search"
        return _done()

    with patch("search_github.subprocess.run", side_effect=run):
        data = _main(["memory leak"], tmp_path, cache=cache)
    assert [r["title"] for r in data["results"]] == ["Cached"]


def test_main_issues_only(tmp_path):
    with patch("search_github.subprocess.run", side_effect=_gh()) as run:
        data = _main(["leak", "--issues-only", "--no-cache"], tmp_path)
    assert len(data["results"]) == 2
    assert not any(c[0][0][:3] == ["gh", "api", "graphql"] for c in run.call_args_list)


def test_main_discussions_only(tmp_path):
    with patch("search_github.subprocess.run", side_effect=_gh()):
        data = _main(["leak", "--discussions-only", "--no-cache"], tmp_path)
    assert [r["source"] for r in data["results"]] == ["github_discussion", "github_discussion"]


def test_main_without_gh_fails(tmp_path):
    with patch("search_github.shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc:
            _main(["leak", "--no-cache"], tmp_path)
    assert exc.value.code == 1
    assert json.loads((tmp_path / "gh.json").read_text(encoding="utf-8"))["error"].startswith("gh CLI not found")


def test_main_rejects_invalid_language(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _main(["leak", "--language", "bad lang", "--no-cache"], tmp_path)
    assert exc.value.code == 1
