#!/usr/bin/env python3
"""Phase 3: Generate Scenario × Test coverage matrix.

Creates comprehensive coverage analysis:
- Which scenarios are tested
- Which scenarios are missing tests
- Test coverage percentage per endpoint
- Visualization in markdown table format
"""

import argparse
import json
import sys
from pathlib import Path

from common.models import CoverageGap, HTTPMethod, Scenario, TestCase
from common.utils import read_json, write_json


def scenario_matches_test_library(scenario: Scenario, test: TestCase) -> bool:
    """
    Library-mode matching: compare method name + branch condition keywords
    against test name, rather than HTTP path + method.
    """
    method_name = scenario.endpoint.lower()       # repurposed as method name
    branch_condition = scenario.input_combination.get("condition", "").lower()
    test_name_lower = test.name.lower()

    # Test name contains method name words
    method_words = set(w for w in method_name.replace(".", "_").split("_") if len(w) > 2)
    condition_words = set(w for w in branch_condition.split() if len(w) > 3)
    test_words = set(test_name_lower.replace("_", " ").split())

    method_match = len(method_words & test_words) >= 1
    cond_match = len(condition_words & test_words) >= 1

    return method_match and cond_match


def scenario_matches_test(scenario: Scenario, test: TestCase) -> bool:
    """
    Check if a test case covers a scenario.

    Matching criteria:
    - Endpoint path matches (exact or pattern)
    - HTTP method matches (if specified in test)
    - Test name suggests coverage (heuristic)

    Args:
        scenario: Scenario to check
        test: Test case to check against

    Returns:
        True if test covers scenario
    """
    # 1. Endpoint match
    if test.tested_endpoint:
        # Normalize paths for comparison
        scenario_path = scenario.endpoint.rstrip("/")
        test_path = test.tested_endpoint.rstrip("/")

        # Exact match
        if scenario_path == test_path:
            pass
        # Pattern match (e.g., /users/:id vs /users/123)
        elif scenario_path.replace("{id}", ":id") == test_path.replace("{id}", ":id"):
            pass
        else:
            return False

    # 2. Method match
    if test.tested_method and test.tested_method != scenario.method:
        return False

    # 3. Scenario type heuristic
    test_name_lower = test.name.lower()

    # Happy path keywords
    if scenario.scenario_type == "happy_path":
        if any(
            keyword in test_name_lower
            for keyword in ["success", "valid", "should_work", "returns_ok", "200"]
        ):
            return True

    # Error case keywords
    elif scenario.scenario_type == "error":
        if any(
            keyword in test_name_lower
            for keyword in [
                "error",
                "invalid",
                "missing",
                "fail",
                "400",
                "404",
                "422",
                "bad_request",
                "not_found",
            ]
        ):
            # Check if specific error matches
            if "missing" in test_name_lower or "required" in test_name_lower:
                if "missing" in scenario.description.lower():
                    return True
            return True

    # Security case keywords
    elif scenario.scenario_type == "security":
        if any(
            keyword in test_name_lower
            for keyword in [
                "xss",
                "injection",
                "sql",
                "security",
                "malicious",
                "attack",
                "exploit",
            ]
        ):
            return True

    # Edge case keywords
    elif scenario.scenario_type == "edge_case":
        if any(
            keyword in test_name_lower
            for keyword in ["edge", "boundary", "limit", "empty", "null", "max", "min"]
        ):
            return True

    # Fallback: if endpoint and method match, assume some coverage
    if test.tested_endpoint and test.tested_method:
        return True

    return False


def find_related_tests(
    scenario: Scenario, all_tests: list[TestCase], mode: str = "api"
) -> list[TestCase]:
    """
    Find all tests related to a scenario.

    Args:
        scenario: Scenario to check
        all_tests: All available test cases
        mode: "api" (HTTP path matching) or "library" (method+branch keyword matching)
    """
    matcher = scenario_matches_test_library if mode == "library" else scenario_matches_test
    return [test for test in all_tests if matcher(scenario, test)]


def generate_coverage_matrix(
    scenarios_file: Path, tests_file: Path, mode: str = "api"
) -> list[CoverageGap]:
    """
    Generate coverage matrix from scenarios and tests.

    Args:
        scenarios_file: Path to scenarios.json
        tests_file: Path to tests.json

    Returns:
        List of CoverageGap objects
    """
    # Load scenarios
    scenarios_data = read_json(scenarios_file)
    scenarios = []

    for scenario_dict in scenarios_data.get("scenarios", []):
        scenario = Scenario(
            endpoint=scenario_dict["endpoint"],
            method=HTTPMethod(scenario_dict["method"]),
            input_combination=scenario_dict["input_combination"],
            expected_output=scenario_dict["expected_output"],
            scenario_type=scenario_dict["scenario_type"],
            description=scenario_dict.get("description", ""),
        )
        scenarios.append(scenario)

    # Load tests
    tests_data = read_json(tests_file)
    tests = []

    for test_dict in tests_data.get("tests", []):
        from common.models import TestFramework

        test = TestCase(
            name=test_dict["name"],
            file_path=test_dict["file_path"],
            line_number=test_dict["line_number"],
            framework=TestFramework(test_dict["framework"]),
            tested_endpoint=test_dict.get("tested_endpoint"),
            tested_method=HTTPMethod(test_dict["tested_method"]) if test_dict.get("tested_method") else None,
            tested_inputs=test_dict.get("tested_inputs", []),
            expected_outputs=test_dict.get("expected_outputs", []),
            test_type=test_dict.get("test_type", "unknown"),
        )
        tests.append(test)

    # Generate coverage gaps
    coverage_gaps = []

    for scenario in scenarios:
        related_tests = find_related_tests(scenario, tests, mode=mode)
        is_tested = len(related_tests) > 0

        gap = CoverageGap(
            scenario=scenario,
            is_tested=is_tested,
            related_tests=related_tests,
        )
        coverage_gaps.append(gap)

    return coverage_gaps


def calculate_coverage_stats(coverage_gaps: list[CoverageGap]) -> dict:
    """
    Calculate coverage statistics.

    Args:
        coverage_gaps: List of coverage gaps

    Returns:
        Dictionary with coverage statistics
    """
    total_scenarios = len(coverage_gaps)
    tested_scenarios = len([g for g in coverage_gaps if g.is_tested])
    untested_scenarios = total_scenarios - tested_scenarios

    coverage_percent = (tested_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

    # Group by endpoint
    endpoint_stats = {}
    for gap in coverage_gaps:
        endpoint_key = f"{gap.scenario.method.value} {gap.scenario.endpoint}"
        if endpoint_key not in endpoint_stats:
            endpoint_stats[endpoint_key] = {
                "total": 0,
                "tested": 0,
                "untested": 0,
            }

        endpoint_stats[endpoint_key]["total"] += 1
        if gap.is_tested:
            endpoint_stats[endpoint_key]["tested"] += 1
        else:
            endpoint_stats[endpoint_key]["untested"] += 1

    # Calculate endpoint coverage percentages
    for stats in endpoint_stats.values():
        stats["coverage_percent"] = (
            (stats["tested"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )

    # Group by scenario type
    type_stats = {}
    for gap in coverage_gaps:
        scenario_type = gap.scenario.scenario_type
        if scenario_type not in type_stats:
            type_stats[scenario_type] = {
                "total": 0,
                "tested": 0,
                "untested": 0,
            }

        type_stats[scenario_type]["total"] += 1
        if gap.is_tested:
            type_stats[scenario_type]["tested"] += 1
        else:
            type_stats[scenario_type]["untested"] += 1

    # Calculate type coverage percentages
    for stats in type_stats.values():
        stats["coverage_percent"] = (
            (stats["tested"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )

    return {
        "total_scenarios": total_scenarios,
        "tested_scenarios": tested_scenarios,
        "untested_scenarios": untested_scenarios,
        "coverage_percent": round(coverage_percent, 2),
        "by_entry_point": endpoint_stats,   # canonical key (works for API + library)
        "by_endpoint": endpoint_stats,      # legacy alias — kept for backward compat
        "by_type": type_stats,
    }


def generate_markdown_table(coverage_gaps: list[CoverageGap]) -> str:
    """
    Generate markdown table visualization.

    Args:
        coverage_gaps: List of coverage gaps

    Returns:
        Markdown table string
    """
    lines = []

    lines.append("# Test Coverage Matrix")
    lines.append("")

    # Group by endpoint
    endpoint_groups = {}
    for gap in coverage_gaps:
        endpoint_key = f"{gap.scenario.method.value} {gap.scenario.endpoint}"
        if endpoint_key not in endpoint_groups:
            endpoint_groups[endpoint_key] = []
        endpoint_groups[endpoint_key].append(gap)

    # Generate table for each endpoint
    for endpoint_key, gaps in sorted(endpoint_groups.items()):
        lines.append(f"## {endpoint_key}")
        lines.append("")

        # Calculate stats
        total = len(gaps)
        tested = len([g for g in gaps if g.is_tested])
        coverage = (tested / total * 100) if total > 0 else 0

        lines.append(f"**Coverage**: {tested}/{total} ({coverage:.1f}%)")
        lines.append("")

        # Table header
        lines.append("| Scenario | Type | Expected | Status | Related Tests |")
        lines.append("|----------|------|----------|--------|---------------|")

        # Table rows
        for gap in gaps:
            scenario = gap.scenario
            status = "✅" if gap.is_tested else "❌"
            test_names = ", ".join([t.name for t in gap.related_tests[:3]])  # Max 3 tests
            if len(gap.related_tests) > 3:
                test_names += f" (+{len(gap.related_tests) - 3} more)"

            lines.append(
                f"| {scenario.description} | {scenario.scenario_type} | {scenario.expected_output} | {status} | {test_names or '-'} |"
            )

        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test coverage matrix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_coverage_matrix.py scenarios.json tests.json
  python generate_coverage_matrix.py scenarios.json tests.json --output matrix.json
  python generate_coverage_matrix.py scenarios.json tests.json --markdown coverage.md
        """,
    )

    parser.add_argument(
        "scenarios_file",
        type=Path,
        help="Path to scenarios.json (from calculate_input_combinations.py)",
    )

    parser.add_argument(
        "tests_file",
        type=Path,
        help="Path to tests.json (from parse_test_files.py)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    parser.add_argument(
        "--markdown",
        "-m",
        type=Path,
        help="Generate markdown table output",
    )

    parser.add_argument(
        "--summary",
        "-s",
        action="store_true",
        help="Show coverage summary",
    )

    parser.add_argument(
        "--mode",
        choices=["api", "library"],
        default="api",
        help="Matching mode: 'api' (HTTP path) or 'library' (method+branch keywords)",
    )

    args = parser.parse_args()

    try:
        # Generate coverage matrix
        coverage_gaps = generate_coverage_matrix(args.scenarios_file, args.tests_file, mode=args.mode)

        # Calculate stats
        stats = calculate_coverage_stats(coverage_gaps)

        # Summary output
        if args.summary:
            print("Coverage Summary:", file=sys.stderr)
            print(f"  Total Scenarios: {stats['total_scenarios']}", file=sys.stderr)
            print(f"  Tested: {stats['tested_scenarios']}", file=sys.stderr)
            print(f"  Untested: {stats['untested_scenarios']}", file=sys.stderr)
            print(f"  Coverage: {stats['coverage_percent']:.2f}%", file=sys.stderr)
            print("", file=sys.stderr)

            print("By Scenario Type:", file=sys.stderr)
            for scenario_type, type_stats in stats["by_type"].items():
                print(
                    f"  {scenario_type}: {type_stats['tested']}/{type_stats['total']} ({type_stats['coverage_percent']:.1f}%)",
                    file=sys.stderr,
                )
            print("", file=sys.stderr)

        # Markdown output
        if args.markdown:
            markdown = generate_markdown_table(coverage_gaps)
            args.markdown.write_text(markdown, encoding="utf-8")
            print(f"Markdown table written to {args.markdown}", file=sys.stderr)

        # JSON output
        output_data = {
            "coverage_stats": stats,
            "gaps": [gap.to_dict() for gap in coverage_gaps],
        }

        write_json(output_data, args.output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
