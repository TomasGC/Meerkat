#!/usr/bin/env python3
"""Tests for search_hashnode module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import SearchQuery, Source, ResultType
from search_hashnode import search_hashnode


@pytest.fixture
def mock_hashnode_response():
    """Mock Hashnode GraphQL API response."""
    return {
        "data": {
            "searchPostsOfPublication": {
                "edges": [
                    {
                        "node": {
                            "title": "Building Scalable APIs with Next.js",
                            "url": "https://example.hashnode.dev/building-scalable-apis",
                            "brief": "A comprehensive guide to building production-ready APIs",
                            "reactionCount": 245,
                            "responseCount": 34,
                            "publishedAt": "2024-01-15T10:00:00Z",
                            "tags": [
                                {"name": "nextjs"},
                                {"name": "api"},
                                {"name": "typescript"}
                            ],
                            "author": {
                                "username": "devauthor1"
                            }
                        }
                    },
                    {
                        "node": {
                            "title": "React Server Components Deep Dive",
                            "url": "https://example.hashnode.dev/react-server-components",
                            "brief": "Understanding the new paradigm of server components",
                            "reactionCount": 189,
                            "responseCount": 28,
                            "publishedAt": "2024-01-20T14:30:00Z",
                            "tags": [
                                {"name": "react"},
                                {"name": "nextjs"},
                                {"name": "frontend"}
                            ],
                            "author": {
                                "username": "devauthor2"
                            }
                        }
                    }
                ]
            }
        }
    }


class TestHashnodeSearch:
    """Test Hashnode search functionality."""

    @patch('search_hashnode.requests.post')
    def test_search_success(self, mock_post, mock_hashnode_response):
        """Test successful Hashnode search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs", "api"])
        response = search_hashnode(query)

        assert response.success is True
        assert len(response.results) == 2

        # Check first result
        result = response.results[0]
        assert result.source == Source.HASHNODE
        assert result.result_type == ResultType.QUESTION
        assert "API" in result.title or "Next.js" in result.title
        assert result.score >= 0
        assert result.url.startswith("https://")
        assert result.repository.startswith("@")

    @patch('search_hashnode.requests.post')
    def test_graphql_query_structure(self, mock_post, mock_hashnode_response):
        """Test GraphQL query is properly formed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        search_hashnode(query)

        # Verify GraphQL request structure
        call_args = mock_post.call_args
        assert call_args[1]["json"]["query"] is not None
        assert "searchPostsOfPublication" in call_args[1]["json"]["query"]
        assert call_args[1]["json"]["variables"]["query"] == "test"

    @patch('search_hashnode.requests.post')
    def test_search_with_tags(self, mock_post, mock_hashnode_response):
        """Test search with tags."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"], tags=["typescript"])
        response = search_hashnode(query)

        assert response.success is True
        # Tags should be included in query string
        call_args = mock_post.call_args
        query_string = call_args[1]["json"]["variables"]["query"]
        assert "nextjs" in query_string

    @patch('search_hashnode.requests.post')
    def test_search_rate_limit(self, mock_post):
        """Test rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = Exception("Rate limited")
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        response = search_hashnode(query)

        assert response.success is False
        assert "error" in response.error.lower()

    @patch('search_hashnode.requests.post')
    def test_search_timeout(self, mock_post):
        """Test timeout handling with retries."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        query = SearchQuery(keywords=["test"])
        response = search_hashnode(query, max_retries=2)

        assert response.success is False
        assert "retry" in response.error.lower() or "timeout" in response.error.lower()
        assert mock_post.call_count == 2

    @patch('search_hashnode.requests.post')
    def test_search_empty_results(self, mock_post):
        """Test handling of no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "searchPostsOfPublication": {
                    "edges": []
                }
            }
        }
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["xyznonexistent"])
        response = search_hashnode(query)

        assert response.success is True
        assert len(response.results) == 0

    @patch('search_hashnode.requests.post')
    def test_excerpt_extraction(self, mock_post, mock_hashnode_response):
        """Test excerpt extraction from brief."""
        # Modify response to have long brief
        mock_hashnode_response["data"]["searchPostsOfPublication"]["edges"][0]["node"]["brief"] = "a" * 300

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True
        # Excerpt should be truncated to 200 chars
        assert len(response.results[0].excerpt) == 200

    @patch('search_hashnode.requests.post')
    def test_excerpt_fallback_to_title(self, mock_post, mock_hashnode_response):
        """Test excerpt fallback when brief is empty."""
        # Remove brief
        mock_hashnode_response["data"]["searchPostsOfPublication"]["edges"][0]["node"]["brief"] = ""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True
        # Excerpt should fallback to title
        assert response.results[0].excerpt == response.results[0].title

    @patch('search_hashnode.requests.post')
    def test_source_attribution(self, mock_post, mock_hashnode_response):
        """Test proper source attribution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True

        for result in response.results:
            assert result.source == Source.HASHNODE
            assert result.source != Source.STACKOVERFLOW
            assert result.source != Source.DEVTO
            assert result.repository.startswith("@")

    @patch('search_hashnode.requests.post')
    def test_tags_parsing(self, mock_post, mock_hashnode_response):
        """Test tags are properly extracted."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True
        result = response.results[0]
        assert len(result.tags) > 0
        assert "nextjs" in result.tags

    @patch('search_hashnode.requests.post')
    def test_created_date_parsing(self, mock_post, mock_hashnode_response):
        """Test publishedAt date parsing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True
        result = response.results[0]
        assert result.created_date is not None
        assert isinstance(result.created_date, datetime)

    @patch('search_hashnode.requests.post')
    def test_cache_integration(self, mock_post, mock_hashnode_response):
        """Test cache hit and miss."""
        from common.cache import SearchCache
        import tempfile

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SearchCache(cache_dir=Path(tmpdir))
            query = SearchQuery(keywords=["nextjs"])

            # First call - cache miss
            response1 = search_hashnode(query, cache=cache)
            assert mock_post.call_count == 1

            # Second call - cache hit
            response2 = search_hashnode(query, cache=cache)
            assert mock_post.call_count == 1  # No additional API call

            assert len(response1.results) == len(response2.results)

    @patch('search_hashnode.requests.post')
    def test_reaction_count_as_score(self, mock_post, mock_hashnode_response):
        """Test reactionCount is used as score."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_hashnode_response
        mock_post.return_value = mock_response

        query = SearchQuery(keywords=["nextjs"])
        response = search_hashnode(query)

        assert response.success is True
        result = response.results[0]
        assert result.score == 245  # From mock data
        assert result.comments == 34  # From mock data
