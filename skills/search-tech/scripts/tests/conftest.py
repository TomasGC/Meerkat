#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures.
"""

import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import SearchQuery, SearchResult, Source, ResultType


@pytest.fixture
def sample_query():
    """Create a sample search query for testing."""
    return SearchQuery(
        keywords=["typescript", "async"],
        tags=["javascript", "async-await"],
        min_score=10,
    )


@pytest.fixture
def sample_stackoverflow_result():
    """Create a sample StackOverflow result."""
    return SearchResult(
        source=Source.STACKOVERFLOW,
        result_type=ResultType.QUESTION,
        title="How to handle async errors in TypeScript?",
        url="https://stackoverflow.com/q/12345678",
        score=125,
        excerpt="When using async/await in TypeScript...",
        tags=["typescript", "async-await", "error-handling"],
        created_date=datetime(2025, 1, 15, 10, 30, 0),
        accepted=True,
        comments=5,
        answer_count=3,
    )


@pytest.fixture
def sample_github_issue():
    """Create a sample GitHub issue result."""
    return SearchResult(
        source=Source.GITHUB_ISSUE,
        result_type=ResultType.ISSUE,
        title="Async error handling improvements",
        url="https://github.com/microsoft/TypeScript/issues/12345",
        score=45,
        excerpt="This issue discusses improvements to async error handling...",
        comments=12,
        status="closed",
        repository="microsoft/TypeScript",
        created_date=datetime(2025, 2, 1, 14, 0, 0),
    )


@pytest.fixture
def sample_github_discussion():
    """Create a sample GitHub discussion result."""
    return SearchResult(
        source=Source.GITHUB_DISCUSSION,
        result_type=ResultType.DISCUSSION,
        title="Best practices for async error handling",
        url="https://github.com/microsoft/TypeScript/discussions/67890",
        score=23,
        excerpt="Let's discuss best practices for handling errors in async functions...",
        comments=8,
        repository="microsoft/TypeScript",
        created_date=datetime(2025, 3, 10, 9, 15, 0),
    )
