#!/usr/bin/env python3
"""Base analyzer class for all project type analyzers.

All analyzers (API, CLI, Mobile, Desktop, Frontend, LLM, SQL) inherit from this base.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import (
    AnalysisResult,
    CoverageGap,
    CoverageMatrix,
    EntryPoint,
    ProjectInfo,
    ProjectType,
    RiskAssessment,
    Scenario,
    TestCase,
)


class BaseAnalyzer(ABC):
    """Base class for all project type analyzers.

    Workflow (same for all analyzers):
    1. can_analyze() - Check if this analyzer handles the project type
    2. extract_entry_points() - Find testable entry points
    3. parse_tests() - Parse test files
    4. generate_scenarios() - Generate test scenarios
    5. generate_coverage_matrix() - Match scenarios to tests
    6. calculate_risks() - Score missing tests by risk
    7. analyze() - Run full pipeline
    """

    @abstractmethod
    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle the project type.

        Args:
            project_info: Project metadata with detected types

        Returns:
            True if this analyzer can handle at least one of the project types
        """
        pass

    @abstractmethod
    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract testable entry points from project.

        Entry points vary by project type:
        - API: HTTP endpoints, GraphQL queries, gRPC methods
        - CLI: Commands, subcommands, flags
        - Mobile: Activities, Fragments, ViewControllers, lifecycle methods
        - Desktop: Windows, Dialogs, event handlers
        - Frontend: Components, hooks, routes
        - LLM: Agent tools, workflows, prompts
        - SQL: Stored procedures, functions, triggers

        Args:
            project_path: Project root directory

        Returns:
            List of entry points found
        """
        pass

    @abstractmethod
    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse test files specific to this project type.

        Args:
            project_path: Project root directory

        Returns:
            List of test cases found
        """
        pass

    @abstractmethod
    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate test scenarios for entry points.

        Scenarios vary by entry point type:
        - HTTP endpoint: happy path, edge cases, errors, security
        - CLI command: valid flags, missing flags, invalid values
        - UI handler: user interactions, lifecycle events
        - Component: props variations, state changes
        - Agent tool: valid inputs, invalid schema, edge cases
        - SQL procedure: valid params, null values, constraint violations

        Args:
            entry_points: Entry points to generate scenarios for

        Returns:
            List of scenarios
        """
        pass

    def generate_coverage_matrix(
        self, scenarios: list[Scenario], tests: list[TestCase]
    ) -> CoverageMatrix:
        """Generate coverage matrix (scenario × test).

        Default implementation uses keyword matching.
        Subclasses can override for smarter matching.

        Args:
            scenarios: All scenarios to test
            tests: All test cases

        Returns:
            Coverage matrix with gaps
        """
        gaps = []
        tested_count = 0

        for scenario in scenarios:
            # Check if scenario is tested
            related_tests = self._find_related_tests(scenario, tests)
            is_tested = len(related_tests) > 0

            if is_tested:
                tested_count += 1

            gaps.append(
                CoverageGap(
                    scenario=scenario, is_tested=is_tested, related_tests=related_tests
                )
            )

        coverage_percent = (
            (tested_count / len(scenarios) * 100) if scenarios else 0.0
        )

        return CoverageMatrix(
            total_scenarios=len(scenarios),
            tested_scenarios=tested_count,
            untested_scenarios=len(scenarios) - tested_count,
            coverage_percent=coverage_percent,
            gaps=gaps,
        )

    def _find_related_tests(
        self, scenario: Scenario, tests: list[TestCase]
    ) -> list[TestCase]:
        """Find tests related to a scenario (keyword matching).

        Args:
            scenario: Scenario to match
            tests: All test cases

        Returns:
            Tests that likely cover this scenario
        """
        related = []

        # Extract keywords from scenario
        scenario_keywords = self._extract_keywords(scenario)

        for test in tests:
            # Extract keywords from test
            test_keywords = self._extract_keywords(test)

            # Check for keyword overlap
            if self._has_keyword_overlap(scenario_keywords, test_keywords):
                related.append(test)

        return related

    def _extract_keywords(self, obj: Any) -> set[str]:
        """Extract keywords from scenario or test.

        Args:
            obj: Scenario or TestCase

        Returns:
            Set of lowercase keywords
        """
        keywords = set()

        if isinstance(obj, Scenario):
            keywords.add(obj.endpoint.lower())
            keywords.add(obj.scenario_type.lower())
            if hasattr(obj, "method") and obj.method is not None:
                m = obj.method
                keywords.add(m.value.lower() if hasattr(m, "value") else str(m).lower())

        elif isinstance(obj, TestCase):
            keywords.add(obj.name.lower())
            if obj.tested_endpoint:
                keywords.add(obj.tested_endpoint.lower())
            keywords.add(obj.test_type.lower())

        return keywords

    def _has_keyword_overlap(self, keywords1: set[str], keywords2: set[str]) -> bool:
        """Check if two keyword sets overlap.

        Args:
            keywords1: First keyword set
            keywords2: Second keyword set

        Returns:
            True if sets have common keywords
        """
        return len(keywords1 & keywords2) > 0

    def calculate_risks(self, coverage_matrix: CoverageMatrix) -> list[RiskAssessment]:
        """Calculate risk scores for missing tests.

        Default implementation uses generic scoring.
        Subclasses can override for domain-specific scoring.

        Args:
            coverage_matrix: Coverage matrix with gaps

        Returns:
            Risk assessments sorted by score (highest first)
        """
        risks = []

        for gap in coverage_matrix.gaps:
            if not gap.is_tested:
                # Generic scoring (subclasses should override for specifics)
                business_impact = self._calculate_business_impact(gap.scenario)
                technical_risk = self._calculate_technical_risk(gap.scenario)
                failure_probability = self._calculate_failure_probability(gap.scenario)

                risk_score = business_impact * technical_risk * failure_probability
                risk_level = RiskAssessment.calculate_risk_level(risk_score)

                risks.append(
                    RiskAssessment(
                        gap=gap,
                        business_impact=business_impact,
                        technical_risk=technical_risk,
                        failure_probability=failure_probability,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        reasoning=self._generate_risk_reasoning(
                            gap.scenario, risk_level
                        ),
                    )
                )

        # Sort by risk score (highest first)
        risks.sort(key=lambda r: r.risk_score, reverse=True)

        return risks

    def _calculate_business_impact(self, scenario: Scenario) -> int:
        """Calculate business impact (1-5).

        Args:
            scenario: Test scenario

        Returns:
            Business impact score
        """
        # Default: moderate impact
        # Subclasses can override with domain-specific logic
        if scenario.scenario_type == "security":
            return 5
        elif scenario.scenario_type == "error":
            return 4
        elif scenario.scenario_type == "happy_path":
            return 3
        else:
            return 2

    def _calculate_technical_risk(self, scenario: Scenario) -> int:
        """Calculate technical risk (1-5).

        Args:
            scenario: Test scenario

        Returns:
            Technical risk score
        """
        # Default: moderate risk
        if scenario.scenario_type == "security":
            return 5
        elif scenario.scenario_type == "edge_case":
            return 4
        else:
            return 3

    def _calculate_failure_probability(self, scenario: Scenario) -> int:
        """Calculate failure probability (1-5).

        Args:
            scenario: Test scenario

        Returns:
            Failure probability score
        """
        # Default: moderate probability
        if scenario.scenario_type == "security":
            return 5
        elif scenario.scenario_type == "error":
            return 4
        else:
            return 3

    def _generate_risk_reasoning(self, scenario: Scenario, risk_level: str) -> str:
        """Generate human-readable risk reasoning.

        Args:
            scenario: Test scenario
            risk_level: Risk level (CRITICAL/HIGH/MEDIUM/LOW)

        Returns:
            Reasoning string
        """
        return (
            f"{risk_level} risk: {scenario.scenario_type} scenario "
            f"for '{scenario.endpoint}' is not tested"
        )

    def analyze(
        self, project_path: Path, project_info: ProjectInfo
    ) -> AnalysisResult:
        """Run full analysis pipeline.

        This method orchestrates the entire workflow:
        1. Extract entry points
        2. Parse tests
        3. Generate scenarios
        4. Calculate coverage
        5. Assess risks

        Args:
            project_path: Project root directory
            project_info: Project metadata

        Returns:
            Complete analysis result
        """
        # Step 1: Extract entry points
        entry_points = self.extract_entry_points(project_path)

        # Step 2: Parse tests
        tests = self.parse_tests(project_path)

        # Step 3: Generate scenarios
        scenarios = self.generate_scenarios(entry_points)

        # Step 4: Calculate coverage
        coverage_matrix = self.generate_coverage_matrix(scenarios, tests)

        # Step 5: Assess risks
        risks = self.calculate_risks(coverage_matrix)

        return AnalysisResult(
            project_type=project_info.primary_type,
            entry_points=entry_points,
            test_cases=tests,
            scenarios=scenarios,
            coverage_matrix=coverage_matrix,
            risk_assessment=risks,
        )
