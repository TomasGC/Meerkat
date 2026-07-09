#!/usr/bin/env python3
"""
Aggregate and rank search results from multiple sources.

Usage:
    python aggregate_results.py stackoverflow.json github.json --output final.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add common to path
sys.path.insert(0, str(Path(__file__).parent))

from common.models import SearchResult, SearchResponse
from common.logger import setup_logger, MetricsCollector, get_defaults


def calculate_rank_score(result: SearchResult) -> float:
    """
    Calculate unified ranking score across sources.

    Factors:
    - Base score (votes/reactions)
    - Accepted answer bonus (+50)
    - Recency bonus (up to +18 for last 6 months)
    - Engagement bonus (comments × 2)

    Args:
        result: Search result

    Returns:
        Calculated rank score
    """
    score = result.score

    # Bonus for accepted answers
    if result.accepted:
        score += 50

    # Bonus for recent results
    if result.created_date:
        days_old = (datetime.now() - result.created_date.replace(tzinfo=None)).days
        if days_old < 180:  # Last 6 months
            recency_bonus = (180 - days_old) / 10
            score += recency_bonus

    # Bonus for high engagement
    engagement = result.comments + result.answer_count
    score += engagement * 2

    return round(score, 2)


def aggregate_results(input_files: list, max_results: int = 10, logger=None, metrics=None) -> list:
    """
    Aggregate results from multiple source files.

    Args:
        input_files: List of JSON file paths
        max_results: Maximum results to return
        logger: Logger instance
        metrics: Metrics collector

    Returns:
        List of top SearchResult objects
    """
    logger, metrics = get_defaults(logger, metrics, __name__)

    all_results = []
    files_loaded = 0
    files_failed = 0

    logger.debug(f"Aggregating results from {len(input_files)} files")

    # Load results from all files
    for file_path in input_files:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            metrics.increment('errors')
            files_failed += 1
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse SearchResponse
            if not data.get("success"):
                error = data.get('error', 'Unknown error')
                logger.warning(f"{file_path}: {error}")
                metrics.increment('errors')
                files_failed += 1
                continue

            # Convert results
            results_count = 0
            for result_data in data.get("results", []):
                result = SearchResult.from_dict(result_data)
                # Calculate rank score
                result.rank_score = calculate_rank_score(result)
                all_results.append(result)
                results_count += 1

            files_loaded += 1
            metrics.increment('total_results', results_count)
            logger.debug(f"Loaded {results_count} results from {path.name}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            metrics.increment('errors')
            files_failed += 1
            continue

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            metrics.increment('errors')
            files_failed += 1
            continue

    logger.info(f"Loaded {files_loaded}/{len(input_files)} files, {len(all_results)} total results")

    if len(all_results) == 0:
        logger.warning("No results to aggregate")
        return []

    # Sort by rank score (descending)
    all_results.sort(key=lambda r: r.rank_score, reverse=True)

    # Take top N
    top_results = all_results[:max_results]

    logger.info(f"Returning top {len(top_results)} results (max: {max_results})")

    return top_results


def format_markdown(results: list, query_str: str) -> str:
    """
    Format results as markdown.

    Args:
        results: List of SearchResult objects
        query_str: Original query string

    Returns:
        Markdown-formatted string
    """
    if not results:
        return f"## 🔍 No results found for \"{query_str}\"\n\n💡 Try:\n- Checking spelling\n- Using more common terms\n- Adding language tags\n"

    lines = [
        f"## 🔍 Technical Search Results for \"{query_str}\"",
        "",
        f"### Top Results ({len(results)} found)",
        ""
    ]

    for i, result in enumerate(results, 1):
        # Source icon
        icon = {
            "stackoverflow": "⭐",
            "github_issue": "🐙",
            "github_discussion": "💬",
            "reddit": "🔴",
            "devto": "📰",
            "hashnode": "✍️",
            "medium": "📝",
        }.get(result.source.value, "📄")

        # Status badge
        status = ""
        if result.accepted:
            status = " | ✅ Accepted"
        elif result.status == "closed":
            status = " | Closed"

        # Title line
        lines.append(f"#### {i}. {icon} {result.score} 👍 | {result.source.value.replace('_', ' ').title()}{status}")
        lines.append(f"**{result.title}**")

        # Tags
        if result.tags:
            tags_str = ", ".join(result.tags[:5])  # Max 5 tags
            lines.append(f"Tags: {tags_str}")

        # Repository (for GitHub)
        if result.repository:
            lines.append(f"Repository: {result.repository}")

        # Source link
        lines.append(f"Source: {result.url}")
        lines.append("")

        # Excerpt
        if result.excerpt:
            lines.append(f"> {result.excerpt}")
            lines.append("")

    # Summary
    lines.append("---")
    lines.append("**Search completed across multiple platforms**")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Aggregate and rank search results from multiple sources"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON result files to aggregate"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)"
    )
    parser.add_argument(
        "--output",
        default="aggregated.json",
        help="Output JSON file (default: aggregated.json)"
    )
    parser.add_argument(
        "--markdown",
        default="",
        help="Also output markdown file (optional)"
    )
    parser.add_argument(
        "--query",
        default="search query",
        help="Original query string for markdown formatting"
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

    # Validate input files
    if not args.files:
        logger.error("No input files provided")
        sys.exit(1)

    # Aggregate results
    results = aggregate_results(args.files, args.max_results, logger=logger, metrics=metrics)

    if not results:
        logger.warning("No results to output")
        output_data = {
            "success": False,
            "error": "No results found in any input file",
            "total_results": 0,
            "results": [],
            "sources": {}
        }
    else:
        output_data = {
            "success": True,
            "total_results": len(results),
            "results": [r.to_dict() for r in results],
            "sources": {}
        }

        # Count sources
        for result in results:
            source = result.source.value
            output_data["sources"][source] = output_data["sources"].get(source, 0) + 1

    # Write JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON output written to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON output: {e}")
        sys.exit(1)

    # Write markdown output if requested
    if args.markdown:
        try:
            markdown_content = format_markdown(results, args.query)
            markdown_path = Path(args.markdown)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)

            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"Markdown output written to {markdown_path}")
        except Exception as e:
            logger.error(f"Failed to write markdown output: {e}")
            sys.exit(1)

    # Print summary
    if results:
        logger.info(f"✅ Aggregated {len(results)} results")
        for source, count in output_data["sources"].items():
            logger.info(f"   - {source}: {count} results")

        if args.verbose:
            logger.info(f"Metrics: {metrics}")
    else:
        logger.warning("❌ No results aggregated")
        sys.exit(1)


if __name__ == "__main__":
    main()
