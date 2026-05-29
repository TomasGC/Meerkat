#!/usr/bin/env python3
"""Phase 5: Universal parallel orchestrator with analyzer routing.

Orchestrates universal project analysis with intelligent analyzer routing:

Phase 0: Multi-type project detection (single process)
Phase 1: Analyzer routing (select appropriate analyzers)
Phase 2: Entry point extraction (parallel per analyzer)
Phase 3: Test parsing (parallel per analyzer)
Phase 4: Scenario generation (parallel per analyzer)
Phase 5: Coverage matrix (aggregate results)
Phase 6: Risk prioritization (aggregate results)

Features:
- Universal project type support (19 types)
- Automatic analyzer routing based on detected types
- Hybrid project support (multiple analyzers in parallel)
- ProcessPoolExecutor for CPU-bound parallelization
- Progress bars with tqdm
- Incremental cache support
- Aggregated results for hybrid projects
"""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from analyzers import (
    APIAnalyzer,
    CLIAnalyzer,
    MobileAnalyzer,
    DesktopAnalyzer,
    FrontendAnalyzer,
    FullstackAnalyzer,
    LLMAnalyzer,
    SQLAnalyzer,
    ServerlessAnalyzer,
    WorkerAnalyzer,
    MessageQueueAnalyzer,
    SmartContractAnalyzer,
)
from common.cache import AnalysisCache
from common.models import ProjectType, AnalysisResult

# Import project detection
from analyze_project_structure import analyze_project as detect_project_structure

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not installed
    class tqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get("total", 0)
            self.n = 0

        def update(self, n=1):
            self.n += n

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass


class AnalyzerRouter:
    """Routes project to appropriate analyzers based on detected types."""

    def __init__(self):
        """Initialize all analyzers."""
        self.analyzers = [
            APIAnalyzer(),
            CLIAnalyzer(),
            MobileAnalyzer(),
            DesktopAnalyzer(),
            FrontendAnalyzer(),
            FullstackAnalyzer(),
            LLMAnalyzer(),
            SQLAnalyzer(),
            ServerlessAnalyzer(),
            WorkerAnalyzer(),
            MessageQueueAnalyzer(),
            SmartContractAnalyzer(),
        ]

    def select_analyzers(self, project_info) -> list:
        """Select analyzers based on detected project types.

        Args:
            project_info: ProjectInfo from analyze_project_structure

        Returns:
            List of analyzers that can handle this project
        """
        selected = []

        for analyzer in self.analyzers:
            if analyzer.can_analyze(project_info):
                selected.append(analyzer)

        if not selected:
            raise ValueError(
                f"No analyzer found for types: {project_info.project_types}"
            )

        return selected

    def analyze_project(
        self,
        project_path: Path,
        max_workers: int = 4,
        verbose: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Route and analyze project with appropriate analyzers.

        Args:
            project_path: Path to project root
            max_workers: Maximum parallel workers
            verbose: Show detailed progress
            use_cache: Use incremental cache

        Returns:
            Aggregated analysis results
        """
        # Phase 0: Detect project types
        if verbose:
            print("\n🔍 Phase 0: Detecting project types...")

        project_info = detect_project_structure(project_path)

        if verbose:
            print(f"  ✅ Language: {project_info.language.value}")
            print(f"  ✅ Frameworks: {', '.join(project_info.frameworks) if project_info.frameworks else 'None'}")
            print(f"  ✅ Project types: {', '.join([pt.value for pt in project_info.project_types])}")
            print(f"  ✅ Primary type: {project_info.primary_type.value}")

        # Phase 1: Select analyzers
        if verbose:
            print("\n📊 Phase 1: Selecting analyzers...")

        analyzers = self.select_analyzers(project_info)

        if verbose:
            print(f"  ✅ Using {len(analyzers)} analyzer(s):")
            for analyzer in analyzers:
                print(f"     - {analyzer.__class__.__name__}")

        # Phase 2-4: Run analyzers in parallel
        if verbose:
            print("\n🚀 Phase 2-4: Running analyzers (parallel)...")

        results = {}

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit analyzer tasks
            futures = {
                executor.submit(
                    analyzer.analyze,
                    project_path,
                    project_info,
                ): analyzer
                for analyzer in analyzers
            }

            # Wait for completion with progress
            with tqdm(total=len(futures), desc="Analyzing", disable=not verbose) as pbar:
                for future in as_completed(futures):
                    analyzer = futures[future]
                    try:
                        result = future.result()
                        results[result.project_type] = result

                        if verbose:
                            print(f"  ✅ {analyzer.__class__.__name__}: {len(result.entry_points)} entry points, {len(result.scenarios)} scenarios")

                    except Exception as e:
                        if verbose:
                            print(f"  ❌ {analyzer.__class__.__name__} failed: {e}")

                    pbar.update(1)

        # Phase 5: Aggregate results (for hybrid projects)
        if len(results) > 1:
            if verbose:
                print("\n🔀 Phase 5: Aggregating hybrid project results...")

            aggregated = self._aggregate_results(results, project_info)
            results[ProjectType.HYBRID] = aggregated

            if verbose:
                print(f"  ✅ Total entry points: {len(aggregated.entry_points)}")
                print(f"  ✅ Total scenarios: {len(aggregated.scenarios)}")
                print(f"  ✅ Overall coverage: {aggregated.coverage_matrix.coverage_percent:.2f}%")

        # Phase 6: Generate final report
        return self._generate_report(project_info, results, verbose)

    def _aggregate_results(
        self,
        results: dict[ProjectType, AnalysisResult],
        project_info,
    ) -> AnalysisResult:
        """Aggregate results from multiple analyzers for hybrid projects.

        Args:
            results: Results from each analyzer
            project_info: Project metadata

        Returns:
            Unified AnalysisResult
        """
        from common.models import CoverageMatrix

        all_entry_points = []
        all_tests = []
        all_scenarios = []
        all_risks = []

        for project_type, result in results.items():
            if project_type != ProjectType.HYBRID:
                all_entry_points.extend(result.entry_points)
                all_tests.extend(result.test_cases)
                all_scenarios.extend(result.scenarios)
                all_risks.extend(result.risk_assessment)

        # Generate unified coverage matrix
        tested_count = sum(
            1
            for scenario in all_scenarios
            if any(
                test.tested_endpoint == scenario.endpoint
                for test in all_tests
            )
        )

        unified_matrix = CoverageMatrix(
            total_scenarios=len(all_scenarios),
            tested_scenarios=tested_count,
            untested_scenarios=len(all_scenarios) - tested_count,
            coverage_percent=(tested_count / len(all_scenarios) * 100) if all_scenarios else 0,
            gaps=[],
        )

        return AnalysisResult(
            project_type=ProjectType.HYBRID,
            entry_points=all_entry_points,
            test_cases=all_tests,
            scenarios=all_scenarios,
            coverage_matrix=unified_matrix,
            risk_assessment=all_risks,
            metadata={
                "component_types": [pt.value for pt in results.keys() if pt != ProjectType.HYBRID],
                "component_count": len(results),
            },
        )

    def _generate_report(
        self,
        project_info,
        results: dict[ProjectType, AnalysisResult],
        verbose: bool,
    ) -> dict[str, Any]:
        """Generate final analysis report.

        Args:
            project_info: Project metadata
            results: Analysis results per type
            verbose: Verbose output

        Returns:
            Final report dictionary
        """
        report = {
            "success": True,
            "project_info": project_info.to_dict(),
            "results": {},
        }

        # Add results per type
        for project_type, result in results.items():
            report["results"][project_type.value] = {
                "entry_points": len(result.entry_points),
                "test_cases": len(result.test_cases),
                "scenarios": len(result.scenarios),
                "coverage": {
                    "total_scenarios": result.coverage_matrix.total_scenarios,
                    "tested_scenarios": result.coverage_matrix.tested_scenarios,
                    "untested_scenarios": result.coverage_matrix.untested_scenarios,
                    "coverage_percent": round(result.coverage_matrix.coverage_percent, 2),
                },
                "risks": {
                    "total": len(result.risk_assessment),
                    "by_level": self._count_risks_by_level(result.risk_assessment),
                },
            }

        # Add summary
        if ProjectType.HYBRID in results:
            hybrid_result = results[ProjectType.HYBRID]
            report["summary"] = {
                "total_entry_points": len(hybrid_result.entry_points),
                "total_scenarios": len(hybrid_result.scenarios),
                "total_tests": len(hybrid_result.test_cases),
                "overall_coverage": round(hybrid_result.coverage_matrix.coverage_percent, 2),
                "total_risks": len(hybrid_result.risk_assessment),
            }
        else:
            # Single-type project
            single_result = list(results.values())[0]
            report["summary"] = {
                "total_entry_points": len(single_result.entry_points),
                "total_scenarios": len(single_result.scenarios),
                "total_tests": len(single_result.test_cases),
                "overall_coverage": round(single_result.coverage_matrix.coverage_percent, 2),
                "total_risks": len(single_result.risk_assessment),
            }

        if verbose:
            print("\n✅ Analysis complete!")
            print(f"   Total entry points: {report['summary']['total_entry_points']}")
            print(f"   Total scenarios: {report['summary']['total_scenarios']}")
            print(f"   Overall coverage: {report['summary']['overall_coverage']}%")

        return report

    def _count_risks_by_level(self, risks) -> dict[str, int]:
        """Count risks by level.

        Args:
            risks: List of RiskAssessment

        Returns:
            Dictionary with counts per level
        """
        counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }

        for risk in risks:
            counts[risk.risk_level] = counts.get(risk.risk_level, 0) + 1

        return counts


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Universal parallel black-box analyzer with automatic routing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parallel_analyzer.py /path/to/project
  python parallel_analyzer.py . --output analysis.json --verbose
  python parallel_analyzer.py ~/myapp --max-workers 8

Supported project types (19):
  - REST API, GraphQL API, gRPC API
  - CLI applications
  - Android apps, iOS apps
  - Windows/Mac/Linux desktop apps
  - React/Vue/Angular frontends
  - Next.js/Remix/SvelteKit fullstack
  - LangChain/CrewAI AI agents
  - SQL projects (stored procedures)
  - Serverless (Lambda, Azure Functions, Cloud Functions)
  - Background workers (Celery, Sidekiq, Bull)
  - Message queues (Kafka, RabbitMQ, SQS)
  - Smart contracts (Solidity, Rust/Solana, Move)
  - Hybrid (multiple types in one project)
        """,
    )

    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to project root directory",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file for final report (default: stdout)",
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable incremental cache (force full analysis)",
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before running",
    )

    args = parser.parse_args()

    # Handle cache clearing
    if args.clear_cache:
        cache = AnalysisCache()
        cache.invalidate_all()
        if args.verbose:
            print("✅ Cache cleared")
        if not args.project_path:
            return 0

    try:
        # Initialize router
        router = AnalyzerRouter()

        # Run analysis
        report = router.analyze_project(
            args.project_path,
            args.max_workers,
            args.verbose,
            use_cache=not args.no_cache,
        )

        # Write output
        if args.output:
            args.output.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            if args.verbose:
                print(f"\n✅ Report written to {args.output}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))

        return 0 if report.get("success", False) else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
