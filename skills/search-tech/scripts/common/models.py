#!/usr/bin/env python3
"""
Data models for technical search results.

Common data structures shared across all search scripts.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import re


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class Source(Enum):
    """Search result sources."""
    STACKOVERFLOW = "stackoverflow"
    GITHUB_ISSUE = "github_issue"
    GITHUB_DISCUSSION = "github_discussion"
    REDDIT = "reddit"
    DEVTO = "devto"
    HASHNODE = "hashnode"
    MEDIUM = "medium"


class ResultType(Enum):
    """Result types."""
    QUESTION = "question"
    ISSUE = "issue"
    DISCUSSION = "discussion"


@dataclass
class SearchQuery:
    """Parsed search query with validation."""
    keywords: List[str]
    tags: List[str] = field(default_factory=list)
    min_score: int = 0
    accepted_only: bool = False
    recent_only: bool = False  # Last 6 months
    language: Optional[str] = None

    def __post_init__(self):
        """Validate query after initialization."""
        self.validate()

    def validate(self):
        """Validate search query parameters."""
        # Keywords validation
        if not self.keywords:
            raise ValidationError("Keywords cannot be empty")

        if len(self.keywords) > 50:
            raise ValidationError("Too many keywords (max 50)")

        for keyword in self.keywords:
            if not keyword or not keyword.strip():
                raise ValidationError("Keywords cannot contain empty strings")
            if len(keyword) > 100:
                raise ValidationError(f"Keyword too long: '{keyword[:50]}...' (max 100 chars)")

        # Tags validation
        if len(self.tags) > 10:
            raise ValidationError("Too many tags (max 10)")

        for tag in self.tags:
            if not re.match(r'^[a-zA-Z0-9\-\.#+]{1,50}$', tag):
                raise ValidationError(
                    f"Invalid tag format: '{tag}' (only alphanumeric, -, ., #, + allowed)"
                )

        # Score validation
        if self.min_score < 0:
            raise ValidationError("min_score cannot be negative")
        if self.min_score > 10000:
            raise ValidationError("min_score too high (max 10000)")

        # Language validation
        if self.language:
            if not re.match(r'^[a-zA-Z0-9\-+#]{1,30}$', self.language):
                raise ValidationError(
                    f"Invalid language format: '{self.language}'"
                )

    def __str__(self) -> str:
        """String representation for display."""
        parts = [" ".join(self.keywords)]
        if self.tags:
            parts.append(f"tags:[{','.join(self.tags)}]")
        if self.min_score > 0:
            parts.append(f"score≥{self.min_score}")
        if self.accepted_only:
            parts.append("accepted-only")
        if self.recent_only:
            parts.append("recent")
        return " ".join(parts)


@dataclass
class SearchResult:
    """Unified search result across all sources."""
    source: Source
    result_type: ResultType
    title: str
    url: str
    score: int  # Votes/upvotes
    excerpt: str
    tags: List[str] = field(default_factory=list)
    created_date: Optional[datetime] = None
    accepted: bool = False
    comments: int = 0
    answer_count: int = 0
    status: Optional[str] = None  # For issues: open/closed
    repository: Optional[str] = None  # For GitHub
    rank_score: float = 0.0  # Calculated ranking score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source.value,
            "type": self.result_type.value,
            "title": self.title,
            "url": self.url,
            "score": self.score,
            "excerpt": self.excerpt,
            "tags": self.tags,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "accepted": self.accepted,
            "comments": self.comments,
            "answer_count": self.answer_count,
            "status": self.status,
            "repository": self.repository,
            "rank_score": self.rank_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """Create from dictionary."""
        created_date = None
        if data.get("created_date"):
            created_date = datetime.fromisoformat(data["created_date"])

        return cls(
            source=Source(data["source"]),
            result_type=ResultType(data["type"]),
            title=data["title"],
            url=data["url"],
            score=data["score"],
            excerpt=data["excerpt"],
            tags=data.get("tags", []),
            created_date=created_date,
            accepted=data.get("accepted", False),
            comments=data.get("comments", 0),
            answer_count=data.get("answer_count", 0),
            status=data.get("status"),
            repository=data.get("repository"),
            rank_score=data.get("rank_score", 0.0),
        )


@dataclass
class SearchResponse:
    """Complete search response with metadata."""
    success: bool
    query: SearchQuery
    results: List[SearchResult] = field(default_factory=list)
    error: Optional[str] = None
    search_time_seconds: float = 0.0
    rate_limit_exceeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "query": {
                "keywords": self.query.keywords,
                "tags": self.query.tags,
                "filters": {
                    "min_score": self.query.min_score,
                    "accepted_only": self.query.accepted_only,
                    "recent_only": self.query.recent_only,
                    "language": self.query.language,
                },
            },
            "results": [r.to_dict() for r in self.results],
            "error": self.error,
            "search_time_seconds": round(self.search_time_seconds, 2),
            "rate_limit_exceeded": self.rate_limit_exceeded,
            "summary": {
                "total_results": len(self.results),
                "sources": self._count_sources(),
            },
        }

    def _count_sources(self) -> Dict[str, int]:
        """Count results per source."""
        counts = {}
        for result in self.results:
            source = result.source.value
            counts[source] = counts.get(source, 0) + 1
        return counts
