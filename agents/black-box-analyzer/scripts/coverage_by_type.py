#!/usr/bin/env python3
"""Coverage breakdown by test type (unit / int_mock / int_real / e2e).

Reads tests.json (from parse_test_files.py) and scenarios.json
(from calculate_input_combinations.py), then produces a per-tier
coverage matrix.  Each tier shows which scenarios it covers and
which are blind spots even across all tiers combined.

Usage:
    python coverage_by_type.py scenarios.json tests.json
    python coverage_by_type.py scenarios.json tests.json --output breakdown.json
    python coverage_by_type.py scenarios.json tests.json --markdown breakdown.md
    python coverage_by_type.py scenarios.json tests.json --mode library
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.models import CoverageGap, HTTPMethod, Scenario, TestCase, TestFramework
from common.utils import read_json, write_json
from generate_coverage_matrix import find_related_tests

TEST_TYPES = ("unit", "int_mock", "int_real", "e2e")


def _load_scenarios(scenarios_file: Path) -> list[Scenario]:
    data = read_json(scenarios_file)
    scenarios = []
    for d in data.get("scenarios", []):
        try:
            method = HTTPMethod(d["method"])
        except ValueError:
            # Non-HTTP scenario (RENDER/CALL/WINDOW/etc.) — use GET as sentinel,
            # method matching is skipped for these in scenario_matches_test
            method = HTTPMethod.GET
        scenarios.append(
            Scenario(
                endpoint=d["endpoint"],
                method=method,
                input_combination=d["input_combination"],
                expected_output=d["expected_output"],
                scenario_type=d["scenario_type"],
                description=d.get("description", ""),
            )
        )
    return scenarios


def _load_tests(tests_file: Path) -> list[TestCase]:
    data = read_json(tests_file)
    tests = []
    for d in data.get("tests", []):
        try:
            framework = TestFramework(d["framework"])
        except ValueError:
            framework = TestFramework.UNKNOWN
        try:
            tested_method = HTTPMethod(d["tested_method"]) if d.get("tested_method") else None
        except ValueError:
            tested_method = None
        tests.append(
            TestCase(
                name=d["name"],
                file_path=d["file_path"],
                line_number=d["line_number"],
                framework=framework,
                tested_endpoint=d.get("tested_endpoint"),
                tested_method=tested_method,
                tested_inputs=d.get("tested_inputs", []),
                expected_outputs=d.get("expected_outputs", []),
                test_type=d.get("test_type", "unknown"),
            )
        )
    return tests


def analyze_by_type(
    scenarios: list[Scenario],
    tests: list[TestCase],
    mode: str = "api",
) -> dict:
    """
    For each test type, compute which scenarios it covers.
    Also compute aggregate: scenarios not covered by ANY type.
    """
    # Bucket tests by type
    buckets: dict[str, list[TestCase]] = {t: [] for t in TEST_TYPES}
    buckets["unknown"] = []
    for test in tests:
        bucket = test.test_type if test.test_type in TEST_TYPES else "unknown"
        buckets[bucket].append(test)

    result: dict[str, dict] = {}

    for tier in TEST_TYPES:
        tier_tests = buckets[tier]
        gaps = []
        for scenario in scenarios:
            related = find_related_tests(scenario, tier_tests, mode=mode)
            gaps.append(
                CoverageGap(
                    scenario=scenario,
                    is_tested=len(related) > 0,
                    related_tests=related,
                )
            )
        tested = sum(1 for g in gaps if g.is_tested)
        total = len(gaps)
        result[tier] = {
            "test_count": len(tier_tests),
            "total_scenarios": total,
            "tested_scenarios": tested,
            "untested_scenarios": total - tested,
            "coverage_percent": round(tested / total * 100, 2) if total else 0.0,
            "gaps": [g.to_dict() for g in gaps if not g.is_tested],
        }

    # Unknown-tier tests (test_type not classified)
    unknown_tests = buckets["unknown"]
    result["unknown"] = {
        "test_count": len(unknown_tests),
        "note": "Tests where test_type could not be inferred",
    }

    # Combined: scenarios covered by ZERO tiers
    all_tests = tests
    absolute_gaps = []
    for scenario in scenarios:
        related = find_related_tests(scenario, all_tests, mode=mode)
        if not related:
            absolute_gaps.append(scenario.to_dict())

    result["combined"] = {
        "total_scenarios": len(scenarios),
        "total_tests": len(tests),
        "absolute_blind_spots": len(absolute_gaps),
        "absolute_blind_spot_percent": round(
            len(absolute_gaps) / len(scenarios) * 100, 2
        ) if scenarios else 0.0,
        "blind_spots": absolute_gaps,
        "by_scenario_type": _breakdown_by_scenario_type(scenarios, tests, mode),
    }

    return result


def _breakdown_by_scenario_type(
    scenarios: list[Scenario],
    tests: list[TestCase],
    mode: str,
) -> dict:
    """Per-scenario-type coverage breakdown across all test tiers."""
    by_type: dict[str, dict] = {}
    for scenario in scenarios:
        stype = scenario.scenario_type
        if stype not in by_type:
            by_type[stype] = {"total": 0, "covered": 0}
        by_type[stype]["total"] += 1
        related = find_related_tests(scenario, tests, mode=mode)
        if related:
            by_type[stype]["covered"] += 1

    for stype, stats in by_type.items():
        stats["coverage_percent"] = (
            round(stats["covered"] / stats["total"] * 100, 2) if stats["total"] else 0.0
        )
    return by_type


def generate_markdown(result: dict) -> str:
    lines = ["# Coverage by Test Type", ""]

    combined = result["combined"]
    lines += [
        "## Summary",
        "",
        f"- Total scenarios: **{combined['total_scenarios']}**",
        f"- Total tests: **{combined['total_tests']}**",
        f"- Absolute blind spots (no tier covers them): **{combined['absolute_blind_spots']}** "
        f"({combined['absolute_blind_spot_percent']}%)",
        "",
        "### By Scenario Type",
        "",
        "| Scenario Type | Total | Covered | Coverage % |",
        "|---|---|---|---|",
    ]
    for stype, stats in combined["by_scenario_type"].items():
        lines.append(
            f"| {stype} | {stats['total']} | {stats['covered']} | {stats['coverage_percent']}% |"
        )

    lines += ["", "---", ""]

    for tier in TEST_TYPES:
        tier_data = result[tier]
        pct = tier_data["coverage_percent"]
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        lines += [
            f"## {tier.upper().replace('_', ' ')} tests",
            "",
            f"Tests in this tier: **{tier_data['test_count']}** | "
            f"Coverage: **{pct}%** `{bar}`",
            f"Scenarios covered: {tier_data['tested_scenarios']} / {tier_data['total_scenarios']}",
            "",
        ]
        uncovered = tier_data["gaps"]
        if uncovered:
            lines += [
                f"### Uncovered scenarios ({len(uncovered)})",
                "",
                "| Scenario | Type | Description |",
                "|---|---|---|",
            ]
            for gap in uncovered[:50]:
                s = gap["scenario"]
                method_str = s.get("method", "?")
                endpoint_str = s.get("endpoint", "?")
                lines.append(
                    f"| `{method_str} {endpoint_str}` | {s['scenario_type']} | {s.get('description', '')[:80]} |"
                )
            if len(uncovered) > 50:
                lines.append(f"| … | … | *{len(uncovered) - 50} more rows omitted* |")
        else:
            lines.append("All scenarios covered by this tier.")
        lines.append("")

    if combined["blind_spots"]:
        lines += [
            "---",
            "",
            f"## Absolute Blind Spots ({len(combined['blind_spots'])})",
            "",
            "Scenarios not covered by ANY test tier:",
            "",
            "| Scenario | Type | Description |",
            "|---|---|---|",
        ]
        for s in combined["blind_spots"][:100]:
            lines.append(
                f"| `{s.get('method', '?')} {s.get('endpoint', '?')}` "
                f"| {s['scenario_type']} | {s.get('description', '')[:80]} |"
            )
        if len(combined["blind_spots"]) > 100:
            lines.append(f"| … | … | *{len(combined['blind_spots']) - 100} more rows omitted* |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Coverage breakdown by test type (unit/int_mock/int_real/e2e)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coverage_by_type.py scenarios.json tests.json
  python coverage_by_type.py scenarios.json tests.json --output breakdown.json
  python coverage_by_type.py scenarios.json tests.json --markdown breakdown.md
  python coverage_by_type.py scenarios.json tests.json --mode library
        """,
    )
    parser.add_argument("scenarios_file", type=Path)
    parser.add_argument("tests_file", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--markdown", "-m", type=Path)
    parser.add_argument(
        "--mode",
        choices=["api", "library"],
        default="api",
        help="Matching mode: api (HTTP path) or library (method+branch keywords)",
    )
    args = parser.parse_args()

    try:
        scenarios = _load_scenarios(args.scenarios_file)
        tests = _load_tests(args.tests_file)

        result = analyze_by_type(scenarios, tests, mode=args.mode)

        if args.markdown:
            args.markdown.write_text(generate_markdown(result), encoding="utf-8")
            print(f"Markdown written to {args.markdown}", file=sys.stderr)

        write_json(result, args.output)
        return 0
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] Invalid input: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
