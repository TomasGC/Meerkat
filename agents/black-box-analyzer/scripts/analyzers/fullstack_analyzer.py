#!/usr/bin/env python3
"""Fullstack Analyzer for Next.js, Remix, SvelteKit applications.

Handles detection and analysis of fullstack frameworks that combine:
- API routes (server-side)
- Pages/Components (client-side)
- Data loading (loaders, server components)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import (
    EntryPoint,
    ProjectInfo,
    ProjectType,
    Scenario,
    TestCase,
)

from .api_analyzer import APIAnalyzer
from .base_analyzer import BaseAnalyzer
from .frontend_analyzer import FrontendAnalyzer


class FullstackAnalyzer(BaseAnalyzer):
    """Analyzer for fullstack frameworks (Next.js/Remix/SvelteKit).

    This analyzer combines API + Frontend analysis since fullstack frameworks
    have both server-side routes and client-side components.
    """

    def __init__(self):
        """Initialize with API and Frontend analyzers."""
        self.api_analyzer = APIAnalyzer()
        self.frontend_analyzer = FrontendAnalyzer()

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle fullstack projects."""
        return ProjectType.FULLSTACK in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract fullstack entry points (API routes + pages/components).

        Returns:
            Combined list of API endpoints and frontend components
        """
        entry_points = []

        # Extract API routes (server-side)
        api_entry_points = self.api_analyzer.extract_entry_points(project_path)
        entry_points.extend(api_entry_points)

        # Extract pages/components (client-side)
        frontend_entry_points = self.frontend_analyzer.extract_entry_points(project_path)
        entry_points.extend(frontend_entry_points)

        # Extract fullstack-specific entry points (loaders, actions)
        entry_points.extend(self._extract_fullstack_specific(project_path))

        return entry_points

    def _extract_fullstack_specific(self, project_path: Path) -> list[EntryPoint]:
        """Extract fullstack-specific entry points (Next.js API routes, Remix loaders, etc.)."""
        # Note: fullstack extraction tracked in #4
        # - Next.js: app/api/* routes, getServerSideProps, getStaticProps
        # - Remix: loader, action functions
        # - SvelteKit: +page.server.ts, +server.ts, load functions
        return []

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse fullstack test files.

        Combines API tests and frontend tests.
        """
        tests = []

        # API tests
        tests.extend(self.api_analyzer.parse_tests(project_path))

        # Frontend tests
        tests.extend(self.frontend_analyzer.parse_tests(project_path))

        return tests

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate fullstack test scenarios.

        Scenarios include both:
        - API scenarios (request/response)
        - Frontend scenarios (component rendering)
        - Integration scenarios (data loading + rendering)
        """
        scenarios = []

        # Generate scenarios using both analyzers
        scenarios.extend(self.api_analyzer.generate_scenarios(entry_points))
        scenarios.extend(self.frontend_analyzer.generate_scenarios(entry_points))

        return scenarios
