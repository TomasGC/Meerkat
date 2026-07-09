#!/usr/bin/env python3
"""Phase 4: Prioritize missing tests by risk score.

Risk scoring formula:
    risk_score = business_impact × technical_risk × failure_probability

Risk levels:
    CRITICAL: ≥ 60
    HIGH: 40-59
    MEDIUM: 20-39
    LOW: < 20

Business impact (1-5):
    5 = Revenue/payment, legal/compliance
    4 = User-facing critical features
    3 = User-facing non-critical
    2 = Internal tools
    1 = Logging, analytics

Technical risk (1-5):
    5 = No error handling, complex logic
    4 = State mutations, concurrent access
    3 = Validation logic
    2 = Simple CRUD
    1 = Static content

Failure probability (1-5):
    5 = Known production incidents
    4 = High complexity
    3 = Moderate complexity
    2 = Simple, well-tested elsewhere
    1 = Trivial
"""

import argparse
import json
import re
import sys
from pathlib import Path

from common.constants import RISK_THRESHOLDS
from common.models import CoverageGap, HTTPMethod, RiskAssessment, Scenario, TestCase
from common.utils import read_json, write_json


def _is_library_scenario(scenario: Scenario) -> bool:
    """Library scenarios store method name (no leading '/') in endpoint field."""
    return not scenario.endpoint.startswith("/")


def assess_business_impact(scenario: Scenario) -> tuple[int, str]:
    """
    Assess business impact of missing test.

    Args:
        scenario: Scenario to assess

    Returns:
        Tuple of (impact_score, reasoning)
    """
    path = scenario.endpoint.lower()
    method = scenario.method
    scenario_type = scenario.scenario_type

    if _is_library_scenario(scenario):
        name = scenario.endpoint.lower()
        if any(k in name for k in ("pay", "bill", "charge", "auth", "crypt", "sign", "token", "secret")):
            return 5, "Security or payment-critical library method"
        if any(k in name for k in ("write", "save", "delete", "remove", "update", "send", "publish")):
            return 4, "Mutating library method"
        if any(k in name for k in ("read", "get", "fetch", "parse", "load", "find")):
            return 3, "Read/parse library method"
        return 2, "Internal utility library method"

    # High-impact keywords
    if any(keyword in path for keyword in ["payment", "billing", "checkout", "order"]):
        return 5, "Payment/revenue-critical endpoint"

    if any(keyword in path for keyword in ["auth", "login", "token", "password"]):
        return 5, "Authentication/security-critical endpoint"

    if any(keyword in path for keyword in ["admin", "config", "settings"]):
        return 4, "Administrative endpoint with potential system-wide impact"

    if any(keyword in path for keyword in ["user", "profile", "account"]):
        if method in (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE):
            return 4, "User-facing write operation"
        else:
            return 3, "User-facing read operation"

    if any(keyword in path for keyword in ["report", "analytics", "log"]):
        return 2, "Internal reporting/analytics endpoint"

    # Default by method
    if method in (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE):
        return 3, "Write operation with moderate business impact"
    else:
        return 2, "Read operation with low business impact"


def assess_technical_risk(scenario: Scenario) -> tuple[int, str]:
    """
    Assess technical risk of missing test.

    Args:
        scenario: Scenario to assess

    Returns:
        Tuple of (risk_score, reasoning)
    """
    method = scenario.method
    scenario_type = scenario.scenario_type
    path = scenario.endpoint.lower()

    if _is_library_scenario(scenario):
        condition = scenario.input_combination.get("condition", "").lower()
        if scenario_type == "security":
            return 5, "Security vulnerability in library"
        if any(k in condition for k in ("null", "none", "nil", "throw", "exception", "overflow")):
            return 4, "Null/exception branch — potential unhandled crash"
        if scenario_type == "error":
            return 3, "Error branch validation"
        if scenario_type == "edge_case":
            return 3, "Edge case handling"
        return 2, "Happy path validation"

    # Security scenarios are high risk
    if scenario_type == "security":
        return 5, "Security vulnerability test (XSS, SQL injection, etc.)"

    # Error handling tests
    if scenario_type == "error":
        # Missing required param tests
        if "missing" in scenario.description.lower():
            return 4, "Missing parameter validation - potential for invalid state"

        # Invalid input tests
        if "invalid" in scenario.description.lower():
            return 3, "Invalid input validation"

        return 3, "Error case validation"

    # Edge cases
    if scenario_type == "edge_case":
        # Null/empty tests
        if "none" in str(scenario.input_combination).lower() or "null" in scenario.description.lower():
            return 4, "Null handling - potential NullPointerException"

        # Boundary values
        if any(
            keyword in scenario.description.lower()
            for keyword in ["max", "min", "boundary", "limit"]
        ):
            return 3, "Boundary value handling"

        return 2, "General edge case"

    # Happy path
    if scenario_type == "happy_path":
        # Write operations are higher risk
        if method in (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH):
            return 3, "Write operation validation"
        elif method == HTTPMethod.DELETE:
            return 4, "Delete operation - potential data loss"
        else:
            return 2, "Read operation validation"

    return 2, "Standard scenario"


def assess_failure_probability(scenario: Scenario) -> tuple[int, str]:
    """
    Assess probability of failure for missing test.

    Args:
        scenario: Scenario to assess

    Returns:
        Tuple of (probability_score, reasoning)
    """
    scenario_type = scenario.scenario_type
    method = scenario.method
    path = scenario.endpoint.lower()

    if _is_library_scenario(scenario):
        condition = scenario.input_combination.get("condition", "").lower()
        if any(k in condition for k in ("null", "none", "nil")):
            return 4, "Null handling frequently causes production issues"
        if scenario_type == "error":
            return 3, "Error branches often not fully covered"
        if scenario_type == "edge_case":
            return 3, "Edge cases moderately likely to fail"
        return 2, "Happy path typically well-tested"

    # Security scenarios have high failure probability if unhandled
    if scenario_type == "security":
        return 5, "Security vulnerabilities commonly exploited if unvalidated"

    # Error cases
    if scenario_type == "error":
        if "missing" in scenario.description.lower():
            return 4, "Missing param handling commonly forgotten"

        return 3, "Error cases often not fully covered"

    # Edge cases with null
    if scenario_type == "edge_case":
        if "none" in str(scenario.input_combination).lower():
            return 4, "Null handling frequently causes production issues"

        if any(
            keyword in scenario.description.lower()
            for keyword in ["empty", "max", "boundary"]
        ):
            return 3, "Edge cases moderately likely to fail"

        return 2, "Edge cases generally handled"

    # Happy path
    if scenario_type == "happy_path":
        return 2, "Happy path typically well-tested"

    return 3, "Moderate failure probability"


def calculate_risk_score(
    business_impact: int,
    technical_risk: int,
    failure_probability: int,
) -> tuple[int, str]:
    """
    Calculate risk score and level.

    Args:
        business_impact: Business impact score (1-5)
        technical_risk: Technical risk score (1-5)
        failure_probability: Failure probability score (1-5)

    Returns:
        Tuple of (risk_score, risk_level)
    """
    risk_score = business_impact * technical_risk * failure_probability

    # Determine risk level
    if risk_score >= RISK_THRESHOLDS["CRITICAL"]:
        risk_level = "CRITICAL"
    elif risk_score >= RISK_THRESHOLDS["HIGH"]:
        risk_level = "HIGH"
    elif risk_score >= RISK_THRESHOLDS["MEDIUM"]:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return risk_score, risk_level


def prioritize_gaps(coverage_gaps: list[CoverageGap]) -> list[RiskAssessment]:
    """
    Prioritize coverage gaps by risk.

    Args:
        coverage_gaps: List of coverage gaps (from generate_coverage_matrix.py)

    Returns:
        List of RiskAssessment objects, sorted by risk score (descending)
    """
    risk_assessments = []

    for gap in coverage_gaps:
        # Skip already tested scenarios
        if gap.is_tested:
            continue

        scenario = gap.scenario

        # Assess each dimension
        business_impact, business_reasoning = assess_business_impact(scenario)
        technical_risk, technical_reasoning = assess_technical_risk(scenario)
        failure_probability, failure_reasoning = assess_failure_probability(scenario)

        # Calculate risk score
        risk_score, risk_level = calculate_risk_score(
            business_impact,
            technical_risk,
            failure_probability,
        )

        # Combine reasoning
        reasoning = f"{business_reasoning}. {technical_reasoning}. {failure_reasoning}."

        # Create risk assessment
        assessment = RiskAssessment(
            gap=gap,
            business_impact=business_impact,
            technical_risk=technical_risk,
            failure_probability=failure_probability,
            risk_score=risk_score,
            risk_level=risk_level,
            reasoning=reasoning,
        )

        risk_assessments.append(assessment)

    # Sort by risk score (descending)
    risk_assessments.sort(key=lambda a: a.risk_score, reverse=True)

    return risk_assessments


def load_coverage_matrix(matrix_file: Path) -> list[CoverageGap]:
    """
    Load coverage gaps from matrix.json.

    Args:
        matrix_file: Path to matrix.json

    Returns:
        List of CoverageGap objects
    """
    matrix_data = read_json(matrix_file)

    coverage_gaps = []

    for gap_dict in matrix_data.get("gaps", []):
        # Reconstruct Scenario
        scenario_dict = gap_dict["scenario"]
        scenario = Scenario(
            endpoint=scenario_dict["endpoint"],
            method=HTTPMethod(scenario_dict["method"]),
            input_combination=scenario_dict["input_combination"],
            expected_output=scenario_dict["expected_output"],
            scenario_type=scenario_dict["scenario_type"],
            description=scenario_dict.get("description", ""),
        )

        # Reconstruct TestCases
        from common.models import TestFramework

        related_tests = []
        for test_dict in gap_dict.get("related_tests", []):
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
            related_tests.append(test)

        # Create CoverageGap
        gap = CoverageGap(
            scenario=scenario,
            is_tested=gap_dict["is_tested"],
            related_tests=related_tests,
        )

        coverage_gaps.append(gap)

    return coverage_gaps


def calculate_risk_stats(risk_assessments: list[RiskAssessment]) -> dict:
    """
    Calculate risk statistics.

    Args:
        risk_assessments: List of risk assessments

    Returns:
        Dictionary with risk statistics
    """
    total = len(risk_assessments)

    by_level = {
        "CRITICAL": len([a for a in risk_assessments if a.risk_level == "CRITICAL"]),
        "HIGH": len([a for a in risk_assessments if a.risk_level == "HIGH"]),
        "MEDIUM": len([a for a in risk_assessments if a.risk_level == "MEDIUM"]),
        "LOW": len([a for a in risk_assessments if a.risk_level == "LOW"]),
    }

    # Average scores
    avg_business_impact = (
        sum(a.business_impact for a in risk_assessments) / total if total > 0 else 0
    )
    avg_technical_risk = (
        sum(a.technical_risk for a in risk_assessments) / total if total > 0 else 0
    )
    avg_failure_probability = (
        sum(a.failure_probability for a in risk_assessments) / total if total > 0 else 0
    )
    avg_risk_score = sum(a.risk_score for a in risk_assessments) / total if total > 0 else 0

    return {
        "total_gaps": total,
        "by_level": by_level,
        "averages": {
            "business_impact": round(avg_business_impact, 2),
            "technical_risk": round(avg_technical_risk, 2),
            "failure_probability": round(avg_failure_probability, 2),
            "risk_score": round(avg_risk_score, 2),
        },
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Prioritize missing tests by risk score",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prioritize_by_risk.py matrix.json
  python prioritize_by_risk.py matrix.json --output risks.json
  python prioritize_by_risk.py matrix.json --min-level HIGH
  python prioritize_by_risk.py matrix.json --summary
        """,
    )

    parser.add_argument(
        "matrix_file",
        type=Path,
        help="Path to matrix.json (from generate_coverage_matrix.py)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    parser.add_argument(
        "--min-level",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default="LOW",
        help="Minimum risk level to include (default: LOW)",
    )

    parser.add_argument(
        "--summary",
        "-s",
        action="store_true",
        help="Show risk summary statistics",
    )

    args = parser.parse_args()

    try:
        # Load coverage matrix
        coverage_gaps = load_coverage_matrix(args.matrix_file)

        # Prioritize gaps
        risk_assessments = prioritize_gaps(coverage_gaps)

        # Filter by minimum level
        level_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        min_level_index = level_order.index(args.min_level)

        filtered_assessments = [
            a for a in risk_assessments if level_order.index(a.risk_level) >= min_level_index
        ]

        # Calculate stats
        stats = calculate_risk_stats(filtered_assessments)

        # Summary output
        if args.summary:
            print("Risk Summary:", file=sys.stderr)
            print(f"  Total Missing Tests: {stats['total_gaps']}", file=sys.stderr)
            print("", file=sys.stderr)

            print("By Risk Level:", file=sys.stderr)
            for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                count = stats["by_level"][level]
                print(f"  {level}: {count}", file=sys.stderr)
            print("", file=sys.stderr)

            print("Average Scores:", file=sys.stderr)
            print(
                f"  Business Impact: {stats['averages']['business_impact']:.2f}/5",
                file=sys.stderr,
            )
            print(
                f"  Technical Risk: {stats['averages']['technical_risk']:.2f}/5",
                file=sys.stderr,
            )
            print(
                f"  Failure Probability: {stats['averages']['failure_probability']:.2f}/5",
                file=sys.stderr,
            )
            print(f"  Risk Score: {stats['averages']['risk_score']:.2f}/125", file=sys.stderr)
            print("", file=sys.stderr)

            # Top 10 highest risks
            print("Top 10 Highest Risk Gaps:", file=sys.stderr)
            for i, assessment in enumerate(filtered_assessments[:10], 1):
                scenario = assessment.gap.scenario
                print(
                    f"  {i}. [{assessment.risk_level}] {scenario.method.value} {scenario.endpoint}",
                    file=sys.stderr,
                )
                print(f"     Score: {assessment.risk_score}/125", file=sys.stderr)
                print(f"     {scenario.description}", file=sys.stderr)
                print("", file=sys.stderr)

        # JSON output
        output_data = {
            "risk_stats": stats,
            "risk_assessments": [a.to_dict() for a in filtered_assessments],
        }

        write_json(output_data, args.output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
