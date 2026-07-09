#!/usr/bin/env python3
"""Compare two analysis runs to track progression and detect regressions.

Usage:
    python diff_analysis.py baseline.json current.json
    python diff_analysis.py baseline.json current.json --output diff.json
    python diff_analysis.py baseline.json current.json --format markdown
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AnalysisDiff:
    """Differences between two analysis runs."""

    # Coverage changes
    old_coverage: float
    new_coverage: float
    coverage_delta: float

    # Gap changes
    old_total_gaps: int
    new_total_gaps: int
    resolved_gaps: int
    new_gaps: int

    # Risk level changes
    old_critical: int
    new_critical: int
    old_high: int
    new_high: int

    # Endpoint-level changes
    improved_endpoints: list[dict]
    regressed_endpoints: list[dict]
    new_endpoints: list[str]
    removed_endpoints: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "coverage": {
                "old": round(self.old_coverage, 2),
                "new": round(self.new_coverage, 2),
                "delta": round(self.coverage_delta, 2),
                "trend": "improved" if self.coverage_delta > 0 else "regressed" if self.coverage_delta < 0 else "unchanged",
            },
            "gaps": {
                "old_total": self.old_total_gaps,
                "new_total": self.new_total_gaps,
                "resolved": self.resolved_gaps,
                "new": self.new_gaps,
                "net_change": self.resolved_gaps - self.new_gaps,
            },
            "risk_levels": {
                "critical": {
                    "old": self.old_critical,
                    "new": self.new_critical,
                    "delta": self.new_critical - self.old_critical,
                },
                "high": {
                    "old": self.old_high,
                    "new": self.new_high,
                    "delta": self.new_high - self.old_high,
                },
            },
            "endpoints": {
                "improved": self.improved_endpoints,
                "regressed": self.regressed_endpoints,
                "new": self.new_endpoints,
                "removed": self.removed_endpoints,
            },
        }


def load_analysis(file_path: Path) -> dict:
    """Load analysis JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {file_path}")

    try:
        return json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def compare_analyses(baseline: dict, current: dict) -> AnalysisDiff:
    """
    Compare two analysis runs.

    Args:
        baseline: Baseline analysis results
        current: Current analysis results

    Returns:
        AnalysisDiff with all differences
    """
    # Extract coverage data
    baseline_coverage = baseline.get("coverage_summary", {})
    current_coverage = current.get("coverage_summary", {})

    old_coverage = baseline_coverage.get("coverage_percent", 0)
    new_coverage = current_coverage.get("coverage_percent", 0)
    coverage_delta = new_coverage - old_coverage

    # Extract gap counts
    old_total_gaps = baseline_coverage.get("untested_scenarios", 0)
    new_total_gaps = current_coverage.get("untested_scenarios", 0)

    # Extract risk levels
    baseline_risk = baseline.get("risk_summary", {}).get("by_level", {})
    current_risk = current.get("risk_summary", {}).get("by_level", {})

    old_critical = baseline_risk.get("CRITICAL", 0)
    new_critical = current_risk.get("CRITICAL", 0)
    old_high = baseline_risk.get("HIGH", 0)
    new_high = current_risk.get("HIGH", 0)

    # Calculate resolved/new gaps
    resolved_gaps = max(0, old_total_gaps - new_total_gaps)
    new_gaps = max(0, new_total_gaps - old_total_gaps)

    # Compare entry-point-level coverage (works for both API endpoints and library methods)
    # "by_entry_point" is the canonical key; fall back to legacy "by_endpoint"
    baseline_by_endpoint = (
        baseline_coverage.get("by_entry_point")
        or baseline_coverage.get("by_endpoint", {})
    )
    current_by_endpoint = (
        current_coverage.get("by_entry_point")
        or current_coverage.get("by_endpoint", {})
    )

    improved_endpoints = []
    regressed_endpoints = []

    for endpoint, current_stats in current_by_endpoint.items():
        if endpoint in baseline_by_endpoint:
            old_cov = baseline_by_endpoint[endpoint].get("coverage_percent", 0)
            new_cov = current_stats.get("coverage_percent", 0)

            if new_cov > old_cov:
                improved_endpoints.append({
                    "endpoint": endpoint,
                    "old_coverage": round(old_cov, 2),
                    "new_coverage": round(new_cov, 2),
                    "delta": round(new_cov - old_cov, 2),
                })
            elif new_cov < old_cov:
                regressed_endpoints.append({
                    "endpoint": endpoint,
                    "old_coverage": round(old_cov, 2),
                    "new_coverage": round(new_cov, 2),
                    "delta": round(new_cov - old_cov, 2),
                })

    # Sort by delta
    improved_endpoints.sort(key=lambda x: x["delta"], reverse=True)
    regressed_endpoints.sort(key=lambda x: x["delta"])

    # Find new/removed endpoints
    new_endpoints = [ep for ep in current_by_endpoint.keys() if ep not in baseline_by_endpoint]
    removed_endpoints = [ep for ep in baseline_by_endpoint.keys() if ep not in current_by_endpoint]

    return AnalysisDiff(
        old_coverage=old_coverage,
        new_coverage=new_coverage,
        coverage_delta=coverage_delta,
        old_total_gaps=old_total_gaps,
        new_total_gaps=new_total_gaps,
        resolved_gaps=resolved_gaps,
        new_gaps=new_gaps,
        old_critical=old_critical,
        new_critical=new_critical,
        old_high=old_high,
        new_high=new_high,
        improved_endpoints=improved_endpoints,
        regressed_endpoints=regressed_endpoints,
        new_endpoints=new_endpoints,
        removed_endpoints=removed_endpoints,
    )


def format_markdown(diff: AnalysisDiff) -> str:
    """Format diff as markdown report."""
    lines = []

    lines.append("# Analysis Comparison Report")
    lines.append("")

    # Coverage summary
    lines.append("## 📊 Coverage Summary")
    lines.append("")

    trend_emoji = "📈" if diff.coverage_delta > 0 else "📉" if diff.coverage_delta < 0 else "➡️"
    lines.append(
        f"{trend_emoji} **Coverage**: {diff.old_coverage:.2f}% → {diff.new_coverage:.2f}% "
        f"({diff.coverage_delta:+.2f}%)"
    )
    lines.append("")

    # Gap summary
    lines.append("## 🎯 Gap Summary")
    lines.append("")
    lines.append(f"- **Resolved**: {diff.resolved_gaps} gaps")
    lines.append(f"- **New**: {diff.new_gaps} gaps")

    net_change = diff.resolved_gaps - diff.new_gaps
    if net_change > 0:
        lines.append(f"- **Net improvement**: {net_change} fewer gaps ✅")
    elif net_change < 0:
        lines.append(f"- **Net regression**: {abs(net_change)} more gaps ⚠️")
    else:
        lines.append("- **Net change**: 0 (stable)")
    lines.append("")

    # Risk levels
    lines.append("## ⚠️ Risk Levels")
    lines.append("")

    critical_delta = diff.new_critical - diff.old_critical
    high_delta = diff.new_high - diff.old_high

    critical_emoji = "✅" if critical_delta <= 0 else "🚨"
    high_emoji = "✅" if high_delta <= 0 else "⚠️"

    lines.append(
        f"{critical_emoji} **CRITICAL**: {diff.old_critical} → {diff.new_critical} "
        f"({critical_delta:+d})"
    )
    lines.append(
        f"{high_emoji} **HIGH**: {diff.old_high} → {diff.new_high} "
        f"({high_delta:+d})"
    )
    lines.append("")

    # Endpoint changes
    if diff.improved_endpoints:
        lines.append("## 📈 Improved Endpoints")
        lines.append("")
        lines.append("| Endpoint | Old | New | Delta |")
        lines.append("|----------|-----|-----|-------|")

        for ep in diff.improved_endpoints[:10]:  # Top 10
            lines.append(
                f"| {ep['endpoint']} | {ep['old_coverage']:.1f}% | "
                f"{ep['new_coverage']:.1f}% | +{ep['delta']:.1f}% |"
            )
        lines.append("")

    if diff.regressed_endpoints:
        lines.append("## 📉 Regressed Endpoints")
        lines.append("")
        lines.append("| Endpoint | Old | New | Delta |")
        lines.append("|----------|-----|-----|-------|")

        for ep in diff.regressed_endpoints[:10]:  # Top 10
            lines.append(
                f"| {ep['endpoint']} | {ep['old_coverage']:.1f}% | "
                f"{ep['new_coverage']:.1f}% | {ep['delta']:.1f}% |"
            )
        lines.append("")

    if diff.new_endpoints:
        lines.append("## ➕ New Endpoints")
        lines.append("")
        for ep in diff.new_endpoints[:20]:
            lines.append(f"- {ep}")
        if len(diff.new_endpoints) > 20:
            lines.append(f"- ... and {len(diff.new_endpoints) - 20} more")
        lines.append("")

    if diff.removed_endpoints:
        lines.append("## ➖ Removed Endpoints")
        lines.append("")
        for ep in diff.removed_endpoints[:20]:
            lines.append(f"- {ep}")
        if len(diff.removed_endpoints) > 20:
            lines.append(f"- ... and {len(diff.removed_endpoints) - 20} more")
        lines.append("")

    return "\n".join(lines)


def format_summary(diff: AnalysisDiff) -> str:
    """Format diff as concise summary for CLI output."""
    lines = []

    # Coverage
    trend_emoji = "📈" if diff.coverage_delta > 0 else "📉" if diff.coverage_delta < 0 else "➡️"
    lines.append(
        f"{trend_emoji} Coverage: {diff.old_coverage:.2f}% → {diff.new_coverage:.2f}% "
        f"({diff.coverage_delta:+.2f}%)"
    )

    # Gaps
    if diff.resolved_gaps > 0:
        lines.append(f"✅ Resolved: {diff.resolved_gaps} gaps")
    if diff.new_gaps > 0:
        lines.append(f"❌ New gaps: {diff.new_gaps}")

    # Critical changes
    critical_delta = diff.new_critical - diff.old_critical
    if critical_delta > 0:
        lines.append(f"🚨 NEW CRITICAL: +{critical_delta} gaps")
    elif critical_delta < 0:
        lines.append(f"✅ Resolved CRITICAL: {abs(critical_delta)} gaps")

    # Regressions
    if diff.regressed_endpoints:
        lines.append(f"⚠️ Regressions: {len(diff.regressed_endpoints)} endpoints")
        for ep in diff.regressed_endpoints[:3]:
            lines.append(f"   - {ep['endpoint']} ({ep['old_coverage']:.1f}% → {ep['new_coverage']:.1f}%)")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Compare two analysis runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python diff_analysis.py baseline.json current.json
  python diff_analysis.py baseline.json current.json --output diff.json
  python diff_analysis.py baseline.json current.json --format markdown > report.md
        """,
    )

    parser.add_argument(
        "baseline",
        type=Path,
        help="Baseline analysis JSON file",
    )

    parser.add_argument(
        "current",
        type=Path,
        help="Current analysis JSON file",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown", "summary"],
        default="summary",
        help="Output format (default: summary)",
    )

    args = parser.parse_args()

    try:
        # Load analyses
        baseline = load_analysis(args.baseline)
        current = load_analysis(args.current)

        # Compare
        diff = compare_analyses(baseline, current)

        # Format output
        if args.format == "json":
            output = json.dumps(diff.to_dict(), indent=2)
        elif args.format == "markdown":
            output = format_markdown(diff)
        else:  # summary
            output = format_summary(diff)

        # Write output
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"✅ Diff report written to {args.output}", file=sys.stderr)
        else:
            print(output)

        # Exit code based on regressions
        if diff.regressed_endpoints or (diff.new_critical - diff.old_critical) > 0:
            return 1  # Regressions found

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
