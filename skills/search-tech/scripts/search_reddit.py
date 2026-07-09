#!/usr/bin/env python3
"""
Search Reddit via REST API (no auth required for read-only).

Usage:
    python search_reddit.py "typescript async" --subreddits programming,typescript
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

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


API_BASE = "https://www.reddit.com"
MAX_RESULTS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2
DEFAULT_SUBREDDITS = ["programming", "learnprogramming", "AskProgramming"]


def search_reddit_subreddit(
    query: SearchQuery,
    subreddit: str,
    logger=None,
    metrics=None,
    max_retries=MAX_RETRIES
) -> list:
    """
    Search a specific subreddit.

    Args:
        query: Parsed search query
        subreddit: Subreddit name (without r/)
        logger: Logger instance
        metrics: Metrics collector
        max_retries: Maximum retry attempts

    Returns:
        List of SearchResult objects
    """
    logger, metrics = get_defaults(logger, metrics, __name__)
    search_query = " ".join(query.keywords)
    logger.debug(f"Searching r/{subreddit} for: {search_query}")

    # Retry logic
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            # Reddit JSON API (no auth needed)
            params = {
                "q": search_query,
                "limit": MAX_RESULTS,
                "sort": "relevance",
                "t": "all",  # Time: all, year, month, week, day
            }

            headers = {
                "User-Agent": "TechnicalSearchBot/1.0"
            }

            response = requests.get(
                f"{API_BASE}/r/{subreddit}/search.json",
                params=params,
                headers=headers,
                timeout=10
            )

            # Rate limit check
            if response.status_code == 429:
                logger.warning(f"Reddit rate limit hit for r/{subreddit}")
                metrics.increment('errors')
                return []

            response.raise_for_status()
            data = response.json()

            # Parse results
            results = []
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                post_data = post.get("data", {})

                # Calculate score
                score = post_data.get("score", 0)

                # Extract excerpt (selftext or title)
                excerpt = post_data.get("selftext", "")[:200]
                if not excerpt:
                    excerpt = post_data.get("title", "")

                result = SearchResult(
                    source=Source.REDDIT,
                    result_type=ResultType.DISCUSSION,
                    title=post_data.get("title", ""),
                    url=f"https://www.reddit.com{post_data.get('permalink', '')}",
                    score=score,
                    excerpt=excerpt.strip(),
                    comments=post_data.get("num_comments", 0),
                    tags=[subreddit],
                    created_date=datetime.fromtimestamp(post_data.get("created_utc", 0)) if post_data.get("created_utc") else None,
                    repository=f"r/{subreddit}",
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} results from r/{subreddit}")
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"Reddit timeout for r/{subreddit} (attempt {attempt + 1}/{max_retries})")
            metrics.increment('errors')
            if attempt < max_retries - 1:
                metrics.increment('retries')
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            logger.error(f"Reddit request error for r/{subreddit}: {e}")
            metrics.increment('errors')
            return []

        except Exception as e:
            logger.error(f"Reddit search error for r/{subreddit}: {e}")
            metrics.increment('errors')
            return []

    return []


def search_reddit(
    query: SearchQuery,
    subreddits: list,
    logger=None,
    metrics=None,
    cache=None
) -> SearchResponse:
    """
    Search multiple subreddits.

    Args:
        query: Parsed search query
        subreddits: List of subreddit names
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
        filters = {"subreddits": subreddits}
        cached_data = cache.get(" ".join(query.keywords), filters)
        if cached_data:
            logger.info("Cache hit for Reddit query")
            metrics.increment('cache_hits')
            return SearchResponse(
                success=True,
                query=query,
                results=[SearchResult.from_dict(r) for r in cached_data.get("results", [])],
                search_time_seconds=time.time() - start_time
            )
        metrics.increment('cache_misses')

    # Search all subreddits
    all_results = []
    for subreddit in subreddits:
        results = search_reddit_subreddit(query, subreddit, logger=logger, metrics=metrics)
        all_results.extend(results)

    # Cache results
    if cache and all_results:
        filters = {"subreddits": subreddits}
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
        description="Search Reddit for technical discussions"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--subreddits",
        default=",".join(DEFAULT_SUBREDDITS),
        help=f"Comma-separated subreddits (default: {','.join(DEFAULT_SUBREDDITS)})"
    )
    parser.add_argument(
        "--output",
        default="reddit.json",
        help="Output JSON file (default: reddit.json)"
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
        subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]

        logger.debug(f"Validated query: {query}")
        logger.debug(f"Subreddits: {subreddits}")

    except ValidationError as e:
        logger.error(f"Invalid query: {e}")
        sys.exit(1)

    # Search
    response = search_reddit(query, subreddits, logger=logger, metrics=metrics, cache=cache)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results from Reddit ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ Reddit search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
