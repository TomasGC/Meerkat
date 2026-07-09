#!/usr/bin/env python3
"""
Search StackOverflow via REST API.

Usage:
    python search_stackoverflow.py "async error handling" --tags typescript --min-score 10
"""

import argparse
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
import time

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


API_BASE = "https://api.stackexchange.com/2.3"
MAX_RESULTS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def search_stackoverflow(
    query: SearchQuery,
    logger=None,
    metrics=None,
    cache=None,
    max_retries=MAX_RETRIES
) -> SearchResponse:
    """
    Search StackOverflow API with retry logic and caching.

    Args:
        query: Parsed search query
        logger: Logger instance
        metrics: Metrics collector
        cache: Search cache
        max_retries: Maximum retry attempts

    Returns:
        SearchResponse with results
    """
    logger, metrics = get_defaults(logger, metrics, __name__)
    start_time = time.time()

    # Check cache first
    if cache:
        filters = {
            "tags": query.tags,
            "min_score": query.min_score,
            "accepted_only": query.accepted_only,
            "recent_only": query.recent_only,
        }
        cached_data = cache.get(" ".join(query.keywords), filters)
        if cached_data:
            logger.info("Cache hit for StackOverflow query")
            metrics.increment('cache_hits')
            return SearchResponse(
                success=cached_data["success"],
                query=query,
                results=[SearchResult.from_dict(r) for r in cached_data.get("results", [])],
                search_time_seconds=time.time() - start_time
            )
        metrics.increment('cache_misses')

    # Build API parameters
    params = {
        "order": "desc",
        "sort": "votes" if query.min_score > 0 else "relevance",
        "q": " ".join(query.keywords),
        "site": "stackoverflow",
        "filter": "withbody",
        "pagesize": MAX_RESULTS,
    }

    if query.tags:
        params["tagged"] = ";".join(query.tags)

    if query.accepted_only:
        params["accepted"] = "True"

    if query.recent_only:
        six_months_ago = datetime.now() - timedelta(days=180)
        params["fromdate"] = int(six_months_ago.timestamp())

    if query.min_score > 0:
        params["min"] = query.min_score

    api_key = os.environ.get("STACKOVERFLOW_API_KEY")
    if api_key:
        params["key"] = api_key

    logger.debug(f"Searching StackOverflow with params: {params}")

    # Retry logic
    last_error = None
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            response = requests.get(
                f"{API_BASE}/search/advanced",
                params=params,
                timeout=10
            )

            # Rate limit
            if response.status_code == 429:
                quota_remaining = response.headers.get("X-RateLimit-Remaining", 0)
                error_msg = f"Rate limit exceeded. Remaining: {quota_remaining}"
                logger.error(error_msg)
                metrics.increment('errors')
                return SearchResponse(
                    success=False,
                    query=query,
                    error=error_msg,
                    rate_limit_exceeded=True,
                    search_time_seconds=time.time() - start_time
                )

            response.raise_for_status()
            data = response.json()

            # Parse results
            results = []
            for item in data.get("items", []):
                body = item.get("body", "")
                clean_body = re.sub(r'<[^>]+>', '', body)
                excerpt = clean_body[:200] + "..." if len(clean_body) > 200 else clean_body

                result = SearchResult(
                    source=Source.STACKOVERFLOW,
                    result_type=ResultType.QUESTION,
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    score=item.get("score", 0),
                    excerpt=excerpt.strip(),
                    tags=item.get("tags", []),
                    created_date=datetime.fromtimestamp(item.get("creation_date", 0)),
                    accepted=item.get("is_answered", False) and item.get("accepted_answer_id") is not None,
                    comments=item.get("comment_count", 0),
                    answer_count=item.get("answer_count", 0),
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} results from StackOverflow")

            # Cache successful response
            if cache and results:
                filters = {
                    "tags": query.tags,
                    "min_score": query.min_score,
                    "accepted_only": query.accepted_only,
                    "recent_only": query.recent_only,
                }
                cache_data = {
                    "success": True,
                    "results": [r.to_dict() for r in results],
                }
                cache.set(" ".join(query.keywords), filters, cache_data)

            return SearchResponse(
                success=True,
                query=query,
                results=results,
                search_time_seconds=time.time() - start_time
            )

        except requests.exceptions.Timeout as e:
            last_error = "StackOverflow API timeout (>10s)"
            logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
            metrics.increment('errors')

        except requests.exceptions.RequestException as e:
            last_error = f"StackOverflow API error: {str(e)}"
            logger.warning(f"Request error on attempt {attempt + 1}/{max_retries}: {e}")
            metrics.increment('errors')

        # Retry with delay
        if attempt < max_retries - 1:
            metrics.increment('retries')
            logger.info(f"Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    # All retries failed
    logger.error(f"All {max_retries} attempts failed: {last_error}")
    return SearchResponse(
        success=False,
        query=query,
        error=last_error or "Unknown error",
        search_time_seconds=time.time() - start_time
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search StackOverflow API for technical solutions"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (e.g., typescript,javascript)"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Minimum score threshold (default: 0)"
    )
    parser.add_argument(
        "--accepted-only",
        action="store_true",
        help="Only show questions with accepted answers"
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Only show results from last 6 months"
    )
    parser.add_argument(
        "--output",
        default="stackoverflow.json",
        help="Output JSON file (default: stackoverflow.json)"
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
        query = SearchQuery(
            keywords=args.query.split(),
            tags=[t.strip() for t in args.tags.split(",") if t.strip()],
            min_score=args.min_score,
            accepted_only=args.accepted_only,
            recent_only=args.recent,
        )

        logger.debug(f"Validated query: {query}")

    except ValidationError as e:
        logger.error(f"Invalid query: {e}")
        sys.exit(1)

    # Search
    response = search_stackoverflow(query, logger=logger, metrics=metrics, cache=cache)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ Search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
