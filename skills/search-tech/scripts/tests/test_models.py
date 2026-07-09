#!/usr/bin/env python3
"""Tests for common.models module."""

import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import (
    Source,
    ResultType,
    SearchQuery,
    SearchResult,
    SearchResponse,
    ValidationError,
)


class TestSearchQueryValidation:
    """Test SearchQuery validation logic."""

    def test_valid_query(self):
        """Test valid query creation."""
        query = SearchQuery(
            keywords=["typescript", "async"],
            tags=["javascript", "node.js"],
            min_score=10,
        )
        assert query.keywords == ["typescript", "async"]
        assert query.tags == ["javascript", "node.js"]
        assert query.min_score == 10

    def test_empty_keywords_raises_error(self):
        """Test that empty keywords raise ValidationError."""
        with pytest.raises(ValidationError, match="Keywords cannot be empty"):
            SearchQuery(keywords=[])

    def test_too_many_keywords_raises_error(self):
        """Test that too many keywords raise ValidationError."""
        keywords = [f"keyword{i}" for i in range(51)]
        with pytest.raises(ValidationError, match="Too many keywords"):
            SearchQuery(keywords=keywords)

    def test_empty_string_in_keywords_raises_error(self):
        """Test that empty string in keywords raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot contain empty strings"):
            SearchQuery(keywords=["valid", "", "also valid"])

    def test_keyword_too_long_raises_error(self):
        """Test that keywords longer than 100 chars raise ValidationError."""
        long_keyword = "x" * 101
        with pytest.raises(ValidationError, match="Keyword too long"):
            SearchQuery(keywords=[long_keyword])

    def test_too_many_tags_raises_error(self):
        """Test that too many tags raise ValidationError."""
        tags = [f"tag{i}" for i in range(11)]
        with pytest.raises(ValidationError, match="Too many tags"):
            SearchQuery(keywords=["valid"], tags=tags)

    def test_invalid_tag_format_raises_error(self):
        """Test that invalid tag format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid tag format"):
            SearchQuery(keywords=["valid"], tags=["valid-tag", "invalid tag with spaces"])

    def test_valid_tags_with_special_chars(self):
        """Test that tags with allowed special chars are valid."""
        query = SearchQuery(
            keywords=["test"],
            tags=["c++", "c#", "node.js", "asp.net"]
        )
        assert query.tags == ["c++", "c#", "node.js", "asp.net"]

    def test_negative_min_score_raises_error(self):
        """Test that negative min_score raises ValidationError."""
        with pytest.raises(ValidationError, match="min_score cannot be negative"):
            SearchQuery(keywords=["test"], min_score=-1)

    def test_min_score_too_high_raises_error(self):
        """Test that min_score > 10000 raises ValidationError."""
        with pytest.raises(ValidationError, match="min_score too high"):
            SearchQuery(keywords=["test"], min_score=10001)

    def test_invalid_language_format_raises_error(self):
        """Test that invalid language format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid language format"):
            SearchQuery(keywords=["test"], language="invalid language with spaces")

    def test_valid_language(self):
        """Test that valid language is accepted."""
        query = SearchQuery(keywords=["test"], language="typescript")
        assert query.language == "typescript"


class TestSearchResult:
    """Test SearchResult data class."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            source=Source.STACKOVERFLOW,
            result_type=ResultType.QUESTION,
            title="Test Question",
            url="https://stackoverflow.com/q/123",
            score=42,
            excerpt="This is a test question",
            tags=["python", "testing"],
        )
        assert result.source == Source.STACKOVERFLOW
        assert result.title == "Test Question"
        assert result.score == 42

    def test_search_result_to_dict(self):
        """Test SearchResult serialization to dict."""
        result = SearchResult(
            source=Source.GITHUB_ISSUE,
            result_type=ResultType.ISSUE,
            title="Test Issue",
            url="https://github.com/org/repo/issues/123",
            score=10,
            excerpt="Test issue body",
            created_date=datetime(2025, 1, 1, 12, 0, 0),
        )
        data = result.to_dict()

        assert data["source"] == "github_issue"
        assert data["type"] == "issue"
        assert data["title"] == "Test Issue"
        assert data["created_date"] == "2025-01-01T12:00:00"

    def test_search_result_from_dict(self):
        """Test SearchResult deserialization from dict."""
        data = {
            "source": "stackoverflow",
            "type": "question",
            "title": "Test",
            "url": "https://example.com",
            "score": 5,
            "excerpt": "Test excerpt",
            "tags": ["tag1"],
            "created_date": "2025-01-01T12:00:00",
            "accepted": True,
            "comments": 3,
            "answer_count": 2,
            "rank_score": 15.5,
        }

        result = SearchResult.from_dict(data)

        assert result.source == Source.STACKOVERFLOW
        assert result.result_type == ResultType.QUESTION
        assert result.title == "Test"
        assert result.accepted is True
        assert result.comments == 3
        assert result.rank_score == 15.5


class TestSearchResponse:
    """Test SearchResponse data class."""

    def test_search_response_success(self):
        """Test successful SearchResponse."""
        query = SearchQuery(keywords=["test"])
        results = [
            SearchResult(
                source=Source.STACKOVERFLOW,
                result_type=ResultType.QUESTION,
                title="Result 1",
                url="https://example.com/1",
                score=10,
                excerpt="Excerpt 1",
            ),
            SearchResult(
                source=Source.GITHUB_ISSUE,
                result_type=ResultType.ISSUE,
                title="Result 2",
                url="https://example.com/2",
                score=5,
                excerpt="Excerpt 2",
            ),
        ]

        response = SearchResponse(
            success=True,
            query=query,
            results=results,
            search_time_seconds=1.5,
        )

        assert response.success is True
        assert len(response.results) == 2
        assert response.search_time_seconds == 1.5

    def test_search_response_to_dict(self):
        """Test SearchResponse serialization."""
        query = SearchQuery(keywords=["test"], tags=["python"])
        response = SearchResponse(
            success=True,
            query=query,
            results=[],
            search_time_seconds=0.5,
        )

        data = response.to_dict()

        assert data["success"] is True
        assert data["query"]["keywords"] == ["test"]
        assert data["query"]["filters"]["min_score"] == 0
        assert data["search_time_seconds"] == 0.5
        assert data["summary"]["total_results"] == 0

    def test_search_response_count_sources(self):
        """Test source counting in response."""
        query = SearchQuery(keywords=["test"])
        results = [
            SearchResult(
                source=Source.STACKOVERFLOW,
                result_type=ResultType.QUESTION,
                title="SO 1",
                url="https://example.com/1",
                score=10,
                excerpt="Test",
            ),
            SearchResult(
                source=Source.STACKOVERFLOW,
                result_type=ResultType.QUESTION,
                title="SO 2",
                url="https://example.com/2",
                score=5,
                excerpt="Test",
            ),
            SearchResult(
                source=Source.GITHUB_ISSUE,
                result_type=ResultType.ISSUE,
                title="GH 1",
                url="https://example.com/3",
                score=3,
                excerpt="Test",
            ),
        ]

        response = SearchResponse(success=True, query=query, results=results)
        data = response.to_dict()

        sources = data["summary"]["sources"]
        assert sources["stackoverflow"] == 2
        assert sources["github_issue"] == 1
