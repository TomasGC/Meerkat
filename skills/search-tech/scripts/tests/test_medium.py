#!/usr/bin/env python3
"""Tests for search_medium module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import SearchQuery, Source, ResultType
from search_medium import search_medium_tag, search_medium


@pytest.fixture
def mock_medium_rss():
    """Mock Medium RSS feed."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Medium - programming</title>
    <item>
      <title>Understanding Async JavaScript Patterns</title>
      <link>https://medium.com/user1/understanding-async-123</link>
      <description><![CDATA[<p>A comprehensive guide to async/await patterns in modern JavaScript</p>]]></description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
      <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">devauthor1</dc:creator>
    </item>
    <item>
      <title>Error Handling Best Practices</title>
      <link>https://medium.com/user2/error-handling-456</link>
      <description><![CDATA[<p>How to handle errors gracefully in asynchronous code</p>]]></description>
      <pubDate>Sat, 20 Jan 2024 14:30:00 GMT</pubDate>
      <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">devauthor2</dc:creator>
    </item>
    <item>
      <title>Python vs JavaScript Performance</title>
      <link>https://medium.com/user3/python-vs-js-789</link>
      <description><![CDATA[<p>Comparing performance characteristics between Python and JavaScript</p>]]></description>
      <pubDate>Thu, 25 Jan 2024 09:15:00 GMT</pubDate>
      <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">devauthor3</dc:creator>
    </item>
  </channel>
</rss>"""


class TestMediumSearch:
    """Test Medium search functionality."""

    @patch('search_medium.requests.get')
    def test_search_tag_success(self, mock_get, mock_medium_rss):
        """Test successful Medium tag search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async", "error"])
        results = search_medium_tag(query, "programming")

        assert len(results) >= 1

        # Check first result
        result = results[0]
        assert result.source == Source.MEDIUM
        assert result.result_type == ResultType.QUESTION
        assert "async" in result.title.lower() or "error" in result.title.lower()
        assert result.url.startswith("https://medium.com/")
        assert result.repository.startswith("@")

    @patch('search_medium.requests.get')
    def test_rss_url_construction(self, mock_get, mock_medium_rss):
        """Test RSS URL is properly constructed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        search_medium_tag(query, "javascript")

        # Verify RSS URL format
        call_args = mock_get.call_args
        assert "https://medium.com/feed/tag/javascript" == call_args[0][0]

    @patch('search_medium.requests.get')
    def test_search_keyword_filtering(self, mock_get, mock_medium_rss):
        """Test client-side keyword filtering."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        # Search for specific term
        query = SearchQuery(keywords=["python"])
        results = search_medium_tag(query, "programming")

        # Should filter to articles containing "python"
        for result in results:
            title_lower = result.title.lower()
            desc_lower = result.excerpt.lower() if result.excerpt else ""
            assert "python" in title_lower or "python" in desc_lower

    @patch('search_medium.requests.get')
    def test_search_timeout(self, mock_get):
        """Test timeout handling."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        query = SearchQuery(keywords=["test"])
        results = search_medium_tag(query, "programming")

        assert len(results) == 0

    @patch('search_medium.requests.get')
    def test_search_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_medium_tag(query, "programming")

        assert len(results) == 0

    @patch('search_medium.requests.get')
    def test_html_removal_from_description(self, mock_get):
        """Test HTML tags are removed from description."""
        rss_with_html = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test Article</title>
      <link>https://medium.com/test</link>
      <description><![CDATA[<p>Test with <strong>HTML</strong> and <em>tags</em></p>]]></description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
      <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">author</dc:creator>
    </item>
  </channel>
</rss>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = rss_with_html
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_medium_tag(query, "programming")

        assert len(results) == 1
        # HTML should be removed
        assert "<p>" not in results[0].excerpt
        assert "<strong>" not in results[0].excerpt
        assert "HTML" in results[0].excerpt
        assert "tags" in results[0].excerpt

    @patch('search_medium.requests.get')
    def test_excerpt_truncation(self, mock_get):
        """Test excerpt truncation to 200 characters."""
        long_description = "a" * 300
        rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test</title>
      <link>https://medium.com/test</link>
      <description>{long_description}</description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
      <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">author</dc:creator>
    </item>
  </channel>
</rss>""".encode()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_medium_tag(query, "programming")

        assert len(results) == 1
        # Should be truncated to 200 + "..."
        assert len(results[0].excerpt) <= 203

    @patch('search_medium.requests.get')
    def test_source_attribution(self, mock_get, mock_medium_rss):
        """Test proper source attribution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        results = search_medium_tag(query, "programming")

        for result in results:
            assert result.source == Source.MEDIUM
            assert result.source != Source.STACKOVERFLOW
            assert result.source != Source.HASHNODE
            assert result.repository.startswith("@")

    @patch('search_medium.requests.get')
    def test_author_extraction(self, mock_get, mock_medium_rss):
        """Test author is properly extracted from dc:creator."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        results = search_medium_tag(query, "programming")

        assert len(results) > 0
        result = results[0]
        assert result.repository == "@devauthor1"

    @patch('search_medium.requests.get')
    def test_missing_author_fallback(self, mock_get):
        """Test fallback when author is missing."""
        rss_no_author = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Test</title>
      <link>https://medium.com/test</link>
      <description>Test description</description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = rss_no_author
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["test"])
        results = search_medium_tag(query, "programming")

        assert len(results) == 1
        assert results[0].repository == "@unknown"

    @patch('search_medium.requests.get')
    def test_date_parsing(self, mock_get, mock_medium_rss):
        """Test pubDate parsing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        results = search_medium_tag(query, "programming")

        assert len(results) > 0
        result = results[0]
        assert result.created_date is not None
        assert isinstance(result.created_date, datetime)

    @patch('search_medium.requests.get')
    def test_score_is_zero(self, mock_get, mock_medium_rss):
        """Test score is 0 (Medium doesn't expose claps in RSS)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        query = SearchQuery(keywords=["async"])
        results = search_medium_tag(query, "programming")

        for result in results:
            assert result.score == 0
            assert result.comments == 0

    @patch('search_medium.search_medium_tag')
    def test_search_multiple_tags(self, mock_search_tag):
        """Test searching across multiple tags."""
        from common.models import SearchResult

        # Mock results from different tags
        mock_search_tag.side_effect = [
            [SearchResult(
                source=Source.MEDIUM,
                result_type=ResultType.QUESTION,
                title="Result from javascript tag",
                url="https://medium.com/1",
                score=0,
                excerpt="Test",
            )],
            [SearchResult(
                source=Source.MEDIUM,
                result_type=ResultType.QUESTION,
                title="Result from programming tag",
                url="https://medium.com/2",
                score=0,
                excerpt="Test",
            )],
        ]

        query = SearchQuery(keywords=["test"])
        response = search_medium(query, ["javascript", "programming"])

        assert response.success is True
        assert len(response.results) == 2
        assert mock_search_tag.call_count == 2

    @patch('search_medium.requests.get')
    def test_cache_integration(self, mock_get, mock_medium_rss):
        """Test cache hit and miss."""
        from common.cache import SearchCache
        import tempfile

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_medium_rss
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SearchCache(cache_dir=Path(tmpdir))
            query = SearchQuery(keywords=["async"])

            # First call - cache miss
            response1 = search_medium(query, ["programming"], cache=cache)
            api_call_count = mock_get.call_count

            # Second call - cache hit
            response2 = search_medium(query, ["programming"], cache=cache)
            assert mock_get.call_count == api_call_count  # No additional API call

            assert len(response1.results) == len(response2.results)
