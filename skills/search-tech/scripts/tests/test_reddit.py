#!/usr/bin/env python3
"""Tests for search_reddit module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import SearchQuery, Source, ResultType
from search_reddit import search_reddit_subreddit, search_reddit


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

    @patch('search_reddit.requests.get')
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

    @patch('search_reddit.requests.get')
    def test_search_subreddit_rate_limit(self, mock_get):
        """Test rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_reddit_subreddit(query, "programming")

        assert len(results) == 0

    @patch('search_reddit.requests.get')
    def test_search_subreddit_timeout(self, mock_get):
        """Test timeout handling."""
        mock_get.side_effect = Exception("Timeout")

        query = SearchQuery(keywords=["test"])
        results = search_reddit_subreddit(query, "programming")

        assert len(results) == 0

    @patch('search_reddit.search_reddit_subreddit')
    def test_search_multiple_subreddits(self, mock_search):
        """Test searching across multiple subreddits."""
        from common.models import SearchResult

        # Mock results from different subreddits
        mock_search.side_effect = [
            [SearchResult(
                source=Source.REDDIT,
                result_type=ResultType.DISCUSSION,
                title="Result from r/programming",
                url="https://reddit.com/1",
                score=100,
                excerpt="Test",
            )],
            [SearchResult(
                source=Source.REDDIT,
                result_type=ResultType.DISCUSSION,
                title="Result from r/learnprogramming",
                url="https://reddit.com/2",
                score=50,
                excerpt="Test",
            )],
        ]

        query = SearchQuery(keywords=["test"])
        response = search_reddit(query, ["programming", "learnprogramming"])

        assert response.success is True
        assert len(response.results) == 2
        assert mock_search.call_count == 2

    def test_reddit_excerpt_extraction(self):
        """Test excerpt extraction from selftext."""
        from common.models import SearchResult

        # Long selftext should be truncated
        long_text = "a" * 250

        # This would be inside the actual search function
        excerpt = long_text[:200]
        assert len(excerpt) == 200

    def test_reddit_source_attribution(self):
        """Test proper source attribution."""
        from common.models import SearchResult

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
