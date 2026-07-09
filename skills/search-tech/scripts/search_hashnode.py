#!/usr/bin/env python3
"""
Search Hashnode via GraphQL API.

Usage:
    python search_hashnode.py "next.js routing" --tags nextjs,react
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


API_BASE = "https://gql.hashnode.com"
MAX_RESULTS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2


def search_hashnode(
    query: SearchQuery,
    logger=None,
    metrics=None,
    cache=None,
    max_retries=MAX_RETRIES
) -> SearchResponse:
    """
    Search Hashnode articles via GraphQL.

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
            logger.info("Cache hit for Hashnode query")
            metrics.increment('cache_hits')
            return SearchResponse(
                success=True,
                query=query,
                results=[SearchResult.from_dict(r) for r in cached_data.get("results", [])],
                search_time_seconds=time.time() - start_time
            )
        metrics.increment('cache_misses')

    search_query = " ".join(query.keywords)
    logger.debug(f"Searching Hashnode for: {search_query}")

    # GraphQL query for searching posts
    graphql_query = """
    query SearchPosts($query: String!, $first: Int!) {
      searchPostsOfPublication(
        publicationId: "56744723958ef13879b9531a"
        first: $first
        filter: { query: $query }
      ) {
        edges {
          node {
            title
            url
            brief
            reactionCount
            responseCount
            publishedAt
            tags {
              name
            }
            author {
              username
            }
          }
        }
      }
    }
    """

    # Retry logic
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "TechnicalSearchBot/1.0"
            }

            payload = {
                "query": graphql_query,
                "variables": {
                    "query": search_query,
                    "first": MAX_RESULTS
                }
            }

            response = requests.post(
                API_BASE,
                json=payload,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            # Parse results
            results = []
            posts = data.get("data", {}).get("searchPostsOfPublication", {}).get("edges", [])

            for edge in posts:
                post = edge.get("node", {})

                # Calculate score (reactions)
                score = post.get("reactionCount", 0)

                # Extract excerpt
                excerpt = post.get("brief", "")[:200]
                if not excerpt:
                    excerpt = post.get("title", "")

                # Parse tags
                tags = [tag.get("name", "") for tag in post.get("tags", [])]

                result = SearchResult(
                    source=Source.HASHNODE,
                    result_type=ResultType.QUESTION,  # Articles as "questions"
                    title=post.get("title", ""),
                    url=post.get("url", ""),
                    score=score,
                    excerpt=excerpt.strip(),
                    comments=post.get("responseCount", 0),
                    tags=tags,
                    created_date=datetime.fromisoformat(post.get("publishedAt", "").replace("Z", "+00:00")) if post.get("publishedAt") else None,
                    repository=f"@{post.get('author', {}).get('username', 'unknown')}",
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} results from Hashnode")

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
            logger.warning(f"Hashnode timeout (attempt {attempt + 1}/{max_retries})")
            metrics.increment('errors')
            if attempt < max_retries - 1:
                metrics.increment('retries')
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            logger.error(f"Hashnode request error: {e}")
            metrics.increment('errors')
            return SearchResponse(
                success=False,
                query=query,
                error=f"Hashnode API error: {str(e)}",
                search_time_seconds=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Hashnode search error: {e}")
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
        description="Search Hashnode for technical articles"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (e.g., nextjs,react)"
    )
    parser.add_argument(
        "--output",
        default="hashnode.json",
        help="Output JSON file (default: hashnode.json)"
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
    response = search_hashnode(query, logger=logger, metrics=metrics, cache=cache)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results from Hashnode ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ Hashnode search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
