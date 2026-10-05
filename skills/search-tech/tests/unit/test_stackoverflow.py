#!/usr/bin/env python3
"""Tests for search_stackoverflow module (HTTP mocked at requests.get)."""

import json
import sys
from unittest.mock import Mock, patch

import pytest
import requests
import search_stackoverflow
from search_stackoverflow import search_stackoverflow as search
from search_tech.cache import SearchCache
from search_tech.logger import MetricsCollector
from search_tech.models import ResultType, SearchQuery, Source

ITEM = {
    "title": "Handle async errors",
    "link": "https://stackoverflow.com/q/1",
    "score": 42,
    "body": "<p>" + "x" * 250 + "</p>",
    "tags": ["typescript"],
    "creation_date": 1700000000,
    "is_answered": True,
    "accepted_answer_id": 7,
    "comment_count": 3,
    "answer_count": 2,
}


def _response(status=200, items=None, headers=None):
    response = Mock(status_code=status, headers=headers or {})
    response.json.return_value = {"items": [ITEM] if items is None else items}
    response.raise_for_status.return_value = None
    return response


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("search_stackoverflow.time.sleep"):
        yield


@patch("search_stackoverflow.requests.get")
def test_search_parses_items(mock_get):
    mock_get.return_value = _response()

    response = search(SearchQuery(keywords=["async", "errors"]))

    assert response.success is True
    result = response.results[0]
    assert (result.source, result.result_type) == (Source.STACKOVERFLOW, ResultType.QUESTION)
    assert (result.title, result.url, result.score) == ("Handle async errors", "https://stackoverflow.com/q/1", 42)
    assert result.excerpt == "x" * 200 + "..."  # HTML stripped, then truncated
    assert result.accepted is True
    assert (result.comments, result.answer_count) == (3, 2)


@patch("search_stackoverflow.requests.get")
def test_search_builds_filters_into_params(mock_get, monkeypatch):
    monkeypatch.setenv("STACKOVERFLOW_API_KEY", "k123")
    mock_get.return_value = _response(items=[])

    search(SearchQuery(keywords=["leak"], tags=["go", "memory"], min_score=5, accepted_only=True, recent_only=True))

    params = mock_get.call_args.kwargs["params"]
    assert params["sort"] == "votes"
    assert params["tagged"] == "go;memory"
    assert params["accepted"] == "True"
    assert params["min"] == 5
    assert params["key"] == "k123"
    assert isinstance(params["fromdate"], int)


@patch("search_stackoverflow.requests.get")
def test_search_without_score_sorts_by_relevance(mock_get, monkeypatch):
    monkeypatch.delenv("STACKOVERFLOW_API_KEY", raising=False)
    mock_get.return_value = _response(items=[])
    search(SearchQuery(keywords=["leak"]))
    params = mock_get.call_args.kwargs["params"]
    assert params["sort"] == "relevance"
    assert "key" not in params and "tagged" not in params


@patch("search_stackoverflow.requests.get")
def test_rate_limit_returns_flagged_failure(mock_get):
    mock_get.return_value = _response(status=429, headers={"X-RateLimit-Remaining": "0"})

    response = search(SearchQuery(keywords=["x"]))

    assert response.success is False
    assert response.rate_limit_exceeded is True
    assert response.error == "Rate limit exceeded. Remaining: 0"


@patch("search_stackoverflow.requests.get")
def test_timeouts_retry_then_fail(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout()
    metrics = MetricsCollector()

    response = search(SearchQuery(keywords=["x"]), metrics=metrics, max_retries=3)

    assert response.success is False
    assert response.error == "StackOverflow API timeout (>10s)"
    assert mock_get.call_count == 3
    assert (metrics.get("errors"), metrics.get("retries")) == (3, 2)


@patch("search_stackoverflow.requests.get")
def test_request_error_then_success(mock_get):
    mock_get.side_effect = [requests.exceptions.ConnectionError("down"), _response()]

    response = search(SearchQuery(keywords=["x"]), max_retries=2)

    assert response.success is True
    assert len(response.results) == 1


@patch("search_stackoverflow.requests.get")
def test_request_error_message_kept_after_last_retry(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("down")
    response = search(SearchQuery(keywords=["x"]), max_retries=1)
    assert response.error == "StackOverflow API error: down"


@patch("search_stackoverflow.requests.get")
def test_cache_hit_skips_api(mock_get, tmp_path):
    mock_get.return_value = _response()
    cache = SearchCache(cache_dir=tmp_path)
    metrics = MetricsCollector()
    query = SearchQuery(keywords=["async"])

    first = search(query, metrics=metrics, cache=cache)
    second = search(query, metrics=metrics, cache=cache)

    assert mock_get.call_count == 1
    assert [r.url for r in second.results] == [r.url for r in first.results]
    assert (metrics.get("cache_misses"), metrics.get("cache_hits")) == (1, 1)


def _main(argv, tmp_path):
    out = tmp_path / "out" / "so.json"
    with patch.object(sys, "argv", ["search_stackoverflow.py", *argv, "--output", str(out), "--no-cache"]):
        search_stackoverflow.main()
    return json.loads(out.read_text(encoding="utf-8"))


@patch("search_stackoverflow.requests.get")
def test_main_writes_response_json(mock_get, tmp_path):
    mock_get.return_value = _response()

    data = _main(["async errors", "--tags", "typescript, node", "--min-score", "3", "--verbose"], tmp_path)

    assert data["success"] is True
    assert len(data["results"]) == 1
    assert mock_get.call_args.kwargs["params"]["tagged"] == "typescript;node"


@patch("search_stackoverflow.requests.get")
def test_main_exits_nonzero_on_failure(mock_get, tmp_path):
    mock_get.return_value = _response(status=429)
    with pytest.raises(SystemExit) as exc:
        _main(["x"], tmp_path)
    assert exc.value.code == 1


def test_main_rejects_invalid_query(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _main(["x", "--tags", "bad tag!"], tmp_path)
    assert exc.value.code == 1
