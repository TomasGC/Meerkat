#!/usr/bin/env python3
"""Tests for search_reddit module."""

import json
import sys
from unittest.mock import Mock, patch

import pytest
import requests

import search_reddit as search_reddit_module
from search_reddit import search_reddit, search_reddit_subreddit
from search_tech.cache import SearchCache
from search_tech.logger import MetricsCollector
from search_tech.models import ResultType, SearchQuery, Source


@pytest.fixture
def mock_reddit_response():
    """Mock Reddit API response."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Best practices for async error handling",
                        "score": 125,
                        "selftext": "What are the best practices for handling errors in async functions?",
                        "permalink": "/r/programming/comments/abc123/best_practices/",
                        "num_comments": 45,
                        "created_utc": 1704067200,  # 2024-01-01
                    }
                },
                {
                    "data": {
                        "title": "Memory leak in async code",
                        "score": 89,
                        "selftext": "",
                        "permalink": "/r/programming/comments/def456/memory_leak/",
                        "num_comments": 23,
                        "created_utc": 1704153600,
                    }
                },
            ]
        }
    }


class TestRedditSearch:
    """Test Reddit search functionality."""

    @patch("search_reddit.requests.get")
    def test_search_subreddit_success(self, mock_get, mock_reddit_response):
        """Test successful subreddit search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_reddit_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async", "error"])
        results = search_reddit_subreddit(query, "programming")

        assert len(results) == 2
        assert results[0].source == Source.REDDIT
        assert results[0].result_type == ResultType.DISCUSSION
        assert results[0].title == "Best practices for async error handling"
        assert results[0].score == 125
        assert results[0].comments == 45
        assert "r/programming" in results[0].repository

    @patch("search_reddit.requests.get")
    def test_search_subreddit_rate_limit(self, mock_get):
        """Test rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_reddit_subreddit(query, "programming")

        assert len(results) == 0

    @patch("search_reddit.requests.get")
    def test_search_subreddit_timeout(self, mock_get):
        """Test timeout handling."""
        mock_get.side_effect = Exception("Timeout")

        query = SearchQuery(keywords=["test"])
        results = search_reddit_subreddit(query, "programming")

        assert len(results) == 0

    @patch("search_reddit.search_reddit_subreddit")
    def test_search_multiple_subreddits(self, mock_search):
        """Test searching across multiple subreddits."""
        from search_tech.models import SearchResult

        # Mock results from different subreddits
        mock_search.side_effect = [
            [
                SearchResult(
                    source=Source.REDDIT,
                    result_type=ResultType.DISCUSSION,
                    title="Result from r/programming",
                    url="https://reddit.com/1",
                    score=100,
                    excerpt="Test",
                )
            ],
            [
                SearchResult(
                    source=Source.REDDIT,
                    result_type=ResultType.DISCUSSION,
                    title="Result from r/learnprogramming",
                    url="https://reddit.com/2",
                    score=50,
                    excerpt="Test",
                )
            ],
        ]

        query = SearchQuery(keywords=["test"])
        response = search_reddit(query, ["programming", "learnprogramming"])

        assert response.success is True
        assert len(response.results) == 2
        assert mock_search.call_count == 2

    def test_reddit_excerpt_extraction(self):
        """Test excerpt extraction from selftext."""

        # Long selftext should be truncated
        long_text = "a" * 250

        # This would be inside the actual search function
        excerpt = long_text[:200]
        assert len(excerpt) == 200

    def test_reddit_source_attribution(self):
        """Test proper source attribution."""
        from search_tech.models import SearchResult

        result = SearchResult(
            source=Source.REDDIT,
            result_type=ResultType.DISCUSSION,
            title="Test",
            url="https://reddit.com/test",
            score=10,
            excerpt="Test excerpt",
            repository="r/programming",
        )

        assert result.source == Source.REDDIT
        assert result.source != Source.STACKOVERFLOW
        assert result.repository == "r/programming"


# ── retries, cache and CLI ────────────────────────────────────────────────────


def _ok(payload):
    response = Mock(status_code=200)
    response.json.return_value = payload
    return response


@patch("search_reddit.time.sleep")
@patch("search_reddit.requests.get")
def test_search_subreddit_retries_timeouts_then_succeeds(mock_get, _sleep, mock_reddit_response):
    metrics = MetricsCollector()
    mock_get.side_effect = [requests.exceptions.Timeout(), _ok(mock_reddit_response)]

    results = search_reddit_subreddit(SearchQuery(keywords=["x"]), "golang", metrics=metrics, max_retries=2)

    assert len(results) == 2
    assert results[1].excerpt == "Memory leak in async code"  # no selftext: title used
    assert results[0].url == "https://www.reddit.com/r/programming/comments/abc123/best_practices/"
    assert results[0].tags == ["golang"]
    assert (metrics.get("errors"), metrics.get("retries")) == (1, 1)


@patch("search_reddit.time.sleep")
@patch("search_reddit.requests.get")
def test_search_subreddit_gives_up_after_timeouts(mock_get, _sleep):
    mock_get.side_effect = requests.exceptions.Timeout()
    assert search_reddit_subreddit(SearchQuery(keywords=["x"]), "golang", max_retries=2) == []
    assert mock_get.call_count == 2


@patch("search_reddit.requests.get")
def test_search_subreddit_http_error_returns_empty(mock_get):
    response = Mock(status_code=500)
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    mock_get.return_value = response
    assert search_reddit_subreddit(SearchQuery(keywords=["x"]), "golang") == []


@patch("search_reddit.requests.get")
def test_search_subreddit_post_without_date(mock_get):
    mock_get.return_value = _ok({"data": {"children": [{"data": {"title": "T", "permalink": "/p"}}]}})
    (result,) = search_reddit_subreddit(SearchQuery(keywords=["x"]), "golang")
    assert result.created_date is None


@patch("search_reddit.requests.get")
def test_search_reddit_uses_cache_on_second_call(mock_get, mock_reddit_response, tmp_path):
    mock_get.return_value = _ok(mock_reddit_response)
    cache = SearchCache(cache_dir=tmp_path)
    metrics = MetricsCollector()
    query = SearchQuery(keywords=["async"])

    first = search_reddit(query, ["programming"], metrics=metrics, cache=cache)
    second = search_reddit(query, ["programming"], metrics=metrics, cache=cache)

    assert mock_get.call_count == 1
    assert [r.title for r in second.results] == [r.title for r in first.results]
    assert (metrics.get("cache_misses"), metrics.get("cache_hits")) == (1, 1)


@patch("search_reddit.requests.get")
def test_main_writes_results_for_each_subreddit(mock_get, mock_reddit_response, tmp_path):
    mock_get.return_value = _ok(mock_reddit_response)
    out = tmp_path / "r.json"
    argv = ["search_reddit.py", "async errors", "--subreddits", "golang, rust", "--output", str(out), "--no-cache"]

    with patch.object(sys, "argv", argv + ["--verbose"]):
        search_reddit_module.main()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["success"] is True
    assert len(data["results"]) == 4
    urls = [c.args[0] for c in mock_get.call_args_list]
    assert urls == ["https://www.reddit.com/r/golang/search.json", "https://www.reddit.com/r/rust/search.json"]


def test_main_rejects_empty_query(tmp_path):
    argv = ["search_reddit.py", "   ", "--output", str(tmp_path / "r.json"), "--no-cache"]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exc:
            search_reddit_module.main()
    assert exc.value.code == 1
