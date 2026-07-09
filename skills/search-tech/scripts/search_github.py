#!/usr/bin/env python3
"""
Search GitHub Issues and Discussions via gh CLI.

Usage:
    python search_github.py "memory leak" --language typescript
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import time
import shutil

# Add common to path
sys.path.insert(0, str(Path(__file__).parent))

from common.models import SearchQuery, SearchResult, SearchResponse, Source, ResultType, ValidationError
from common.logger import setup_logger, MetricsCollector, get_defaults
from common.cache import SearchCache


MAX_RESULTS_PER_TYPE = 5
MAX_RETRIES = 3
RETRY_DELAY = 2


def check_gh_cli(logger=None) -> tuple[bool, str]:
    """
    Check if gh CLI is installed and authenticated.

    Returns:
        Tuple of (is_available, error_message)
    """
    if logger is None:
        logger = setup_logger(__name__)

    # Check if gh is installed
    if not shutil.which("gh"):
        return False, "gh CLI not found. Install from https://cli.github.com/"

    # Check if authenticated
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "gh CLI not authenticated. Run: gh auth login"

        logger.debug("gh CLI is installed and authenticated")
        return True, ""

    except subprocess.TimeoutExpired:
        return False, "gh CLI authentication check timeout"
    except Exception as e:
        return False, f"gh CLI check error: {e}"


def search_github_issues(
    query: SearchQuery,
    logger=None,
    metrics=None,
    max_retries=MAX_RETRIES
) -> list:
    """
    Search GitHub issues via gh CLI with retry logic.

    Args:
        query: Parsed search query
        logger: Logger instance
        metrics: Metrics collector
        max_retries: Maximum retry attempts

    Returns:
        List of SearchResult objects
    """
    logger, metrics = get_defaults(logger, metrics, __name__)

    # Check gh CLI
    is_available, error = check_gh_cli(logger)
    if not is_available:
        logger.error(error)
        return []

    # Build search query
    search_terms = " ".join(query.keywords)
    if query.language:
        search_terms += f" language:{query.language}"

    search_terms += " sort:reactions-+1"

    logger.debug(f"Searching GitHub issues: {search_terms}")

    # Retry logic
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            cmd = [
                "gh", "search", "issues",
                search_terms,
                "--limit", str(MAX_RESULTS_PER_TYPE),
                "--json", "title,url,state,comments,createdAt,reactions,repository,body"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"gh search issues failed (attempt {attempt + 1}/{max_retries}): {result.stderr}")
                metrics.increment('errors')
                if attempt < max_retries - 1:
                    metrics.increment('retries')
                    time.sleep(RETRY_DELAY)
                    continue
                return []

            issues = json.loads(result.stdout)

            # Convert to SearchResult
            results = []
            for issue in issues:
                reactions = issue.get("reactions", {})
                score = reactions.get("+1", 0) + reactions.get("hooray", 0) + reactions.get("heart", 0)

                # Extract excerpt from body
                body = issue.get("body", "")
                excerpt = body[:200] + "..." if len(body) > 200 else body
                if not excerpt:
                    repo = issue.get('repository', {}).get('nameWithOwner', 'unknown')
                    excerpt = f"Issue in {repo}"

                result = SearchResult(
                    source=Source.GITHUB_ISSUE,
                    result_type=ResultType.ISSUE,
                    title=issue.get("title", ""),
                    url=issue.get("url", ""),
                    score=score,
                    excerpt=excerpt.strip(),
                    comments=issue.get("comments", 0),
                    status=issue.get("state", "unknown"),
                    repository=issue.get("repository", {}).get("nameWithOwner"),
                    created_date=datetime.fromisoformat(issue.get("createdAt", "").replace("Z", "+00:00")) if issue.get("createdAt") else None,
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} GitHub issues")
            return results

        except subprocess.TimeoutExpired:
            logger.warning(f"GitHub issues timeout (attempt {attempt + 1}/{max_retries})")
            metrics.increment('errors')
            if attempt < max_retries - 1:
                metrics.increment('retries')
                time.sleep(RETRY_DELAY)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GitHub issues response: {e}")
            metrics.increment('errors')
            return []

        except Exception as e:
            logger.error(f"GitHub issues search error: {e}")
            metrics.increment('errors')
            return []

    return []


def search_github_discussions(
    query: SearchQuery,
    logger=None,
    metrics=None,
    max_retries=MAX_RETRIES
) -> list:
    """
    Search GitHub discussions via GitHub GraphQL API through gh CLI.

    Uses gh api graphql to search discussions across repositories.

    Args:
        query: Parsed search query
        logger: Logger instance
        metrics: Metrics collector
        max_retries: Maximum retry attempts

    Returns:
        List of SearchResult objects
    """
    logger, metrics = get_defaults(logger, metrics, __name__)

    # Check gh CLI
    is_available, error = check_gh_cli(logger)
    if not is_available:
        logger.error(error)
        return []

    # Build search query for GraphQL
    search_query = " ".join(query.keywords)
    if query.language:
        search_query += f" language:{query.language}"

    # GraphQL query to search discussions
    graphql_query = """
    query($query: String!, $limit: Int!) {
      search(query: $query, type: DISCUSSION, first: $limit) {
        nodes {
          ... on Discussion {
            title
            url
            createdAt
            upvoteCount
            comments {
              totalCount
            }
            repository {
              nameWithOwner
            }
            body
            category {
              name
            }
          }
        }
      }
    }
    """

    logger.debug(f"Searching GitHub discussions: {search_query}")

    # Retry logic
    for attempt in range(max_retries):
        try:
            metrics.increment('api_calls')

            # Call gh api graphql
            result = subprocess.run(
                [
                    "gh", "api", "graphql",
                    "-f", f"query={graphql_query}",
                    "-f", f"query={search_query}",
                    "-F", f"limit={MAX_RESULTS_PER_TYPE}"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"gh api graphql failed (attempt {attempt + 1}/{max_retries}): {result.stderr}")
                metrics.increment('errors')
                if attempt < max_retries - 1:
                    metrics.increment('retries')
                    time.sleep(RETRY_DELAY)
                    continue
                return []

            data = json.loads(result.stdout)

            # Parse discussions
            results = []
            discussions = data.get("data", {}).get("search", {}).get("nodes", [])

            for disc in discussions:
                if not disc:
                    continue

                # Extract excerpt from body
                body = disc.get("body", "")
                excerpt = body[:200] + "..." if len(body) > 200 else body
                if not excerpt:
                    repo = disc.get('repository', {}).get('nameWithOwner', 'unknown')
                    category = disc.get('category', {}).get('name', '')
                    excerpt = f"Discussion in {repo}"
                    if category:
                        excerpt += f" ({category})"

                result = SearchResult(
                    source=Source.GITHUB_DISCUSSION,
                    result_type=ResultType.DISCUSSION,
                    title=disc.get("title", ""),
                    url=disc.get("url", ""),
                    score=disc.get("upvoteCount", 0),
                    excerpt=excerpt.strip(),
                    comments=disc.get("comments", {}).get("totalCount", 0),
                    repository=disc.get("repository", {}).get("nameWithOwner"),
                    created_date=datetime.fromisoformat(disc.get("createdAt", "").replace("Z", "+00:00")) if disc.get("createdAt") else None,
                )
                results.append(result)

            metrics.increment('total_results', len(results))
            logger.info(f"Found {len(results)} GitHub discussions")
            return results

        except subprocess.TimeoutExpired:
            logger.warning(f"GitHub discussions timeout (attempt {attempt + 1}/{max_retries})")
            metrics.increment('errors')
            if attempt < max_retries - 1:
                metrics.increment('retries')
                time.sleep(RETRY_DELAY)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GitHub discussions response: {e}")
            metrics.increment('errors')
            return []

        except Exception as e:
            logger.error(f"GitHub discussions search error: {e}")
            metrics.increment('errors')
            return []

    return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search GitHub Issues and Discussions"
    )
    parser.add_argument(
        "query",
        help="Search query keywords"
    )
    parser.add_argument(
        "--language",
        default="",
        help="Programming language filter (e.g., typescript)"
    )
    parser.add_argument(
        "--issues-only",
        action="store_true",
        help="Search only issues (skip discussions)"
    )
    parser.add_argument(
        "--discussions-only",
        action="store_true",
        help="Search only discussions (skip issues)"
    )
    parser.add_argument(
        "--output",
        default="github.json",
        help="Output JSON file (default: github.json)"
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
            language=args.language if args.language else None,
        )

        logger.debug(f"Validated query: {query}")

    except ValidationError as e:
        logger.error(f"Invalid query: {e}")
        sys.exit(1)

    start_time = time.time()

    # Check cache
    results = []
    if cache and not args.issues_only and not args.discussions_only:
        filters = {"language": query.language, "type": "all"}
        cached_data = cache.get(" ".join(query.keywords), filters)
        if cached_data:
            logger.info("Cache hit for GitHub query")
            metrics.increment('cache_hits')
            results = [SearchResult.from_dict(r) for r in cached_data.get("results", [])]

    # Search if not cached
    if not results:
        metrics.increment('cache_misses')

        # Search issues
        if not args.discussions_only:
            issues = search_github_issues(query, logger=logger, metrics=metrics)
            results.extend(issues)

        # Search discussions
        if not args.issues_only:
            discussions = search_github_discussions(query, logger=logger, metrics=metrics)
            results.extend(discussions)

        # Cache results
        if cache and results:
            filters = {"language": query.language, "type": "all"}
            cache_data = {
                "success": True,
                "results": [r.to_dict() for r in results],
            }
            cache.set(" ".join(query.keywords), filters, cache_data)

    # Create response
    is_available, error = check_gh_cli(logger)
    response = SearchResponse(
        success=len(results) > 0 or is_available,
        query=query,
        results=results,
        error=None if is_available else error,
        search_time_seconds=time.time() - start_time
    )

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    if response.success:
        logger.info(f"✅ Found {len(response.results)} results from GitHub ({response.search_time_seconds:.2f}s)")
        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.error(f"❌ GitHub search failed: {response.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
