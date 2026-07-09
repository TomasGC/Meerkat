#!/usr/bin/env python3
"""Tests for search_devto module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import SearchQuery, Source, ResultType
from search_devto import search_devto


@pytest.fixture
def mock_devto_response():
    """Mock Dev.to API response."""
    return [
        {
            "title": "Understanding Async Patterns in JavaScript",
            "description": "A comprehensive guide to async/await patterns",
            "url": "https://dev.to/user1/understanding-async-123",
            "positive_reactions_count": 245,
            "comments_count": 34,
            "tag_list": ["javascript", "async", "webdev"],
            "published_at": "2024-01-15T10:00:00Z",
            "user": {
                "username": "devuser1"
            }
        },
        {
            "title": "Error Handling Best Practices",
            "description": "How to handle errors gracefully in modern apps",
            "url": "https://dev.to/user2/error-handling-456",
            "positive_reactions_count": 178,
            "comments_count": 22,
            "tag_list": ["programming", "bestpractices", "javascript"],
            "published_at": "2024-01-20T14:30:00Z",
            "user": {
                "username": "devuser2"
            }
        },
        {
            "title": "Python vs JavaScript Performance",
            "description": "Comparing performance characteristics",
            "url": "https://dev.to/user3/python-vs-js-789",
            "positive_reactions_count": 89,
            "comments_count": 15,
            "tag_list": ["python", "javascript", "performance"],
            "published_at": "2024-01-25T09:15:00Z",
            "user": {
                "username": "devuser3"
            }
        }
    ]


class TestDevtoSearch:
    """Test Dev.to search functionality."""

    @patch('search_devto.requests.get')
    def test_search_success(self, mock_get, mock_devto_response):
        """Test successful Dev.to search with keyword filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async", "error"])
        response = search_devto(query)

        assert response.success is True
        assert len(response.results) >= 1

        # Check first result
        result = response.results[0]
        assert result.source == Source.DEVTO
        assert result.result_type == ResultType.QUESTION
        assert "async" in result.title.lower() or "error" in result.title.lower()
        assert result.score >= 0
        assert result.url.startswith("https://dev.to/")
        assert result.repository.startswith("@")

    @patch('search_devto.requests.get')
    def test_search_with_tags(self, mock_get, mock_devto_response):
        """Test search with tag filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"], tags=["javascript"])
        response = search_devto(query)

        assert response.success is True

        # Verify tag was used in API call
        call_args = mock_get.call_args
        assert "tag" in call_args[1]["params"]
        assert call_args[1]["params"]["tag"] == "javascript"

    @patch('search_devto.requests.get')
    def test_search_keyword_filtering(self, mock_get, mock_devto_response):
        """Test client-side keyword filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        # Search for specific term that matches only one article
        query = SearchQuery(keywords=["python"])
        response = search_devto(query)

        assert response.success is True
        # Should filter down to articles containing "python"
        for result in response.results:
            title_lower = result.title.lower()
            desc_lower = result.excerpt.lower() if result.excerpt else ""
            tags_lower = [t.lower() for t in result.tags]

            assert ("python" in title_lower or
                   "python" in desc_lower or
                   "python" in tags_lower)

    @patch('search_devto.requests.get')
    def test_search_rate_limit(self, mock_get):
        """Test rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        response = search_devto(query)

        # Should not raise, should return error response
        assert response.success is False
        assert "error" in response.error.lower()

    @patch('search_devto.requests.get')
    def test_search_timeout(self, mock_get):
        """Test timeout handling with retries."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        query = SearchQuery(keywords=["test"])
        response = search_devto(query, max_retries=2)

        assert response.success is False
        assert "retry" in response.error.lower() or "timeout" in response.error.lower()

        # Should have attempted retries
        assert mock_get.call_count == 2

    @patch('search_devto.requests.get')
    def test_search_empty_results(self, mock_get):
        """Test handling of no matching results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["xyznonexistent"])
        response = search_devto(query)

        assert response.success is True
        assert len(response.results) == 0

    @patch('search_devto.requests.get')
    def test_excerpt_truncation(self, mock_get, mock_devto_response):
        """Test excerpt truncation to 200 characters."""
        # Modify response to have long description
        mock_devto_response[0]["description"] = "a" * 300

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        response = search_devto(query)

        assert response.success is True
        assert len(response.results) > 0
        # Excerpt should be truncated to 200 chars
        assert len(response.results[0].excerpt) <= 200

    @patch('search_devto.requests.get')
    def test_source_attribution(self, mock_get, mock_devto_response):
        """Test proper source attribution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        response = search_devto(query)

        assert response.success is True

        for result in response.results:
            assert result.source == Source.DEVTO
            assert result.source != Source.STACKOVERFLOW
            assert result.source != Source.REDDIT
            assert result.repository.startswith("@")  # Author attribution

    @patch('search_devto.requests.get')
    def test_created_date_parsing(self, mock_get, mock_devto_response):
        """Test published date parsing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        response = search_devto(query)

        assert response.success is True
        assert len(response.results) > 0

        # Check date was parsed correctly
        result = response.results[0]
        assert result.created_date is not None
        assert isinstance(result.created_date, datetime)

    @patch('search_devto.requests.get')
    def test_cache_integration(self, mock_get, mock_devto_response):
        """Test cache hit and miss."""
        from common.cache import SearchCache
        import tempfile

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_devto_response
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SearchCache(cache_dir=Path(tmpdir))
            query = SearchQuery(keywords=["async"])

            # First call - cache miss
            response1 = search_devto(query, cache=cache)
            assert mock_get.call_count == 1

            # Second call - cache hit
            response2 = search_devto(query, cache=cache)
            assert mock_get.call_count == 1  # No additional API call

            assert len(response1.results) == len(response2.results)
