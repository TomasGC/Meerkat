#!/usr/bin/env python3
"""
Search Dev.to via REST API.

Usage:
    python search_devto.py "react hooks" --tags react,javascript
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


API_BASE = "https://dev.to/api"
MAX_RESULTS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2


def search_devto(
    query: SearchQuery,
    logger=None,
    metrics=None,
    cache=None,
    max_retries=MAX_RETRIES
) -> SearchResponse:
    """
    Search Dev.to articles.

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

    # Check cache
    if cache:
        filters = {"tags": query.tags}
        cached_data = cache.get(" ".join(query.keywords), filters)
        if cached_data:
            logger.info("Cache hit for Dev.to query")
            metrics.increment('cache_hits')
            return SearchResponse(
                success=True,
                query=query,
                results=[SearchResult.from_dict(r) for r in cached_data.get("results", [])],
                search_time_seconds=time.time() - start_time
            )
        metrics.increment('cache_misses')

    logger.debug(f"Searching Dev.to for: {' '.join(query.keywords)}")

    # Retry logic
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            # Dev.to API - search articles
            params = {
                "per_page": MAX_RESULTS * 3,  # Get more to filter later
            }

            # Add tag filter if specified
            if query.tags:
                params["tag"] = query.tags[0]  # Dev.to only supports one tag at a time

            headers = {
                "User-Agent": "TechnicalSearchBot/1.0"
            }

            response = requests.get(
                f"{API_BASE}/articles",
                params=params,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            articles = response.json()

            # Filter by keywords (Dev.to API doesn't have full-text search)
            search_terms = [kw.lower() for kw in query.keywords]
            filtered_articles = []

            for article in articles:
                title = article.get("title", "").lower()
                description = article.get("description", "").lower()
                tags = [t.lower() for t in article.get("tag_list", [])]

                # Check if any keyword matches title, description, or tags
                if any(term in title or term in description or term in " ".join(tags) for term in search_terms):
                    filtered_articles.append(article)

                if len(filtered_articles) >= MAX_RESULTS:
                    break

            # Convert to SearchResult
            results = []
            for article in filtered_articles[:MAX_RESULTS]:
                # Calculate score (reactions)
                score = article.get("positive_reactions_count", 0)

                # Extract excerpt
                excerpt = article.get("description", "")[:200]
                if not excerpt:
                    excerpt = article.get("title", "")

                result = SearchResult(
                    source=Source.DEVTO,
                    result_type=ResultType.QUESTION,  # Articles as "questions"
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    score=score,
                    excerpt=excerpt.strip(),
                    comments=article.get("comments_count", 0),
                    tags=article.get("tag_list", []),
                    created_date=datetime.fromisoformat(article.get("published_at", "").replace("Z", "+00:00")) if article.get("published_at") else None,
                    repository=f"@{article.get('user', {}).get('username', 'unknown')}",
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} results from Dev.to")

            # Cache results
            if cache and results:
                filters = {"tags": query.tags}
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

        except requests.exceptions.Timeout:
            logger.warning(f"Dev.to timeout (attempt {attempt + 1}/{max_retries})")
            metrics.increment('errors')
            if attempt < max_retries - 1:
                metrics.increment('retries')
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            logger.error(f"Dev.to request error: {e}")
            metrics.increment('errors')
            return SearchResponse(
                success=False,
                query=query,
                error=f"Dev.to API error: {str(e)}",
                search_time_seconds=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Dev.to search error: {e}")
            metrics.increment('errors')
            return SearchResponse(
                success=False,
                query=query,
                error=f"Unexpected error: {str(e)}",
                search_time_seconds=time.time() - start_time
            )

    return SearchResponse(
        success=False,
        query=query,
        error="All retry attempts failed",
        search_time_seconds=time.time() - start_time
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Dev.to for technical articles"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (e.g., react,javascript)"
    )
    parser.add_argument(
        "--output",
        default="devto.json",
        help="Output JSON file (default: devto.json)"
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
        )

        logger.debug(f"Validated query: {query}")

    except ValidationError as e:
        logger.error(f"Invalid query: {e}")
        sys.exit(1)

    # Search
    response = search_devto(query, logger=logger, metrics=metrics, cache=cache)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results from Dev.to ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ Dev.to search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
