#!/usr/bin/env python3
"""
Search Medium via RSS feeds and tag search.

Usage:
    python search_medium.py "react state management" --tags react,javascript
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# Add common to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

from common.models import SearchQuery, SearchResult, SearchResponse, Source, ResultType, ValidationError
from common.logger import setup_logger, MetricsCollector, get_defaults
from common.cache import SearchCache


MEDIUM_BASE = "https://medium.com"
MAX_RESULTS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2


def search_medium_tag(
    query: SearchQuery,
    tag: str,
    logger=None,
    metrics=None
) -> list:
    """
    Search Medium by tag via RSS feed.

    Args:
        query: Parsed search query
        tag: Medium tag name
        logger: Logger instance
        metrics: Metrics collector

    Returns:
        List of SearchResult objects
    """
    logger, metrics = get_defaults(logger, metrics, __name__)

    try:
        metrics.increment('api_calls')

        # Medium RSS feed for tag
        rss_url = f"{MEDIUM_BASE}/feed/tag/{tag}"
        headers = {
            "User-Agent": "TechnicalSearchBot/1.0"
        }

        response = requests.get(rss_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        # Get items from RSS feed
        results = []
        search_terms = [kw.lower() for kw in query.keywords]

        for item in root.findall('.//item')[:MAX_RESULTS * 2]:  # Get more to filter
            title = item.find('title').text if item.find('title') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

            # Filter by keywords
            if not any(term in title.lower() or term in description.lower() for term in search_terms):
                continue

            # Extract author
            creator = item.find('{http://purl.org/dc/elements/1.1/}creator')
            author = creator.text if creator is not None else "unknown"

            # Parse excerpt from description (remove HTML)
            import re
            clean_desc = re.sub(r'<[^>]+>', '', description)
            excerpt = clean_desc[:200] + "..." if len(clean_desc) > 200 else clean_desc

            # Parse date
            created_date = None
            if pub_date:
                try:
                    created_date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    pass

            result = SearchResult(
                source=Source.MEDIUM,
                result_type=ResultType.QUESTION,  # Articles as "questions"
                title=title,
                url=link,
                score=0,  # Medium doesn't expose claps in RSS
                excerpt=excerpt.strip(),
                comments=0,
                tags=[tag],
                created_date=created_date,
                repository=f"@{author}",
            )
            results.append(result)

            if len(results) >= MAX_RESULTS:
                break

        logger.info(f"Found {len(results)} results from Medium tag '{tag}'")
        return results

    except requests.exceptions.Timeout:
        logger.warning(f"Medium timeout for tag '{tag}'")
        metrics.increment('errors')
        return []

    except Exception as e:
        logger.error(f"Medium search error for tag '{tag}': {e}")
        metrics.increment('errors')
        return []


def search_medium(
    query: SearchQuery,
    tags: list,
    logger=None,
    metrics=None,
    cache=None
) -> SearchResponse:
    """
    Search Medium across multiple tags.

    Args:
        query: Parsed search query
        tags: List of Medium tags
        logger: Logger instance
        metrics: Metrics collector
        cache: Search cache

    Returns:
        SearchResponse with results
    """
    logger, metrics = get_defaults(logger, metrics, __name__)

    start_time = time.time()

    # Check cache
    if cache:
        filters = {"tags": tags}
        cached_data = cache.get(" ".join(query.keywords), filters)
        if cached_data:
            logger.info("Cache hit for Medium query")
            metrics.increment('cache_hits')
            return SearchResponse(
                success=True,
                query=query,
                results=[SearchResult.from_dict(r) for r in cached_data.get("results", [])],
                search_time_seconds=time.time() - start_time
            )
        metrics.increment('cache_misses')

    # Search all tags
    all_results = []
    for tag in tags:
        results = search_medium_tag(query, tag, logger=logger, metrics=metrics)
        all_results.extend(results)

    metrics.increment('total_results', len(all_results))

    # Cache results
    if cache and all_results:
        filters = {"tags": tags}
        cache_data = {
            "success": True,
            "results": [r.to_dict() for r in all_results],
        }
        cache.set(" ".join(query.keywords), filters, cache_data)

    return SearchResponse(
        success=True,
        query=query,
        results=all_results,
        search_time_seconds=time.time() - start_time
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Medium for technical articles"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--tags",
        default="programming",
        help="Comma-separated Medium tags (default: programming)"
    )
    parser.add_argument(
        "--output",
        default="medium.json",
        help="Output JSON file (default: medium.json)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug output"
    )

    args = parser.parse_args()

    # Setup logger
    logger = setup_logger(__name__, verbose=args.verbose, debug=args.debug)

    # Setup metrics
    metrics = MetricsCollector()

    # Setup cache
    cache = None if args.no_cache else SearchCache()

    try:
        # Parse and validate query
        query = SearchQuery(keywords=args.query.split())
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

        logger.debug(f"Validated query: {query}")
        logger.debug(f"Tags: {tags}")

    except ValidationError as e:
        logger.error(f"Invalid query: {e}")
        sys.exit(1)

    # Search
    response = search_medium(query, tags, logger=logger, metrics=metrics, cache=cache)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results from Medium ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ Medium search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
