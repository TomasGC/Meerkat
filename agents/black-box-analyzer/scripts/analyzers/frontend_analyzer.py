#!/usr/bin/env python3
"""Frontend Analyzer for React, Vue, Angular applications.

Handles detection and analysis of frontend frameworks:
- React: Components, hooks, routes
- Vue: Components, composables, Composition API
- Angular: Components, services, modules
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import FRONTEND_PATTERNS
from common.models import (
    EntryPoint,
    EntryPointType,
    Parameter,
    ProjectInfo,
    ProjectType,
    Scenario,
    TestCase,
)
from common.utils import (
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_analyzer import BaseAnalyzer


class FrontendAnalyzer(BaseAnalyzer):
    """Analyzer for frontend applications (React/Vue/Angular)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle frontend projects."""
        return any(
            pt in project_info.project_types
            for pt in {
                ProjectType.FRONTEND_REACT,
                ProjectType.FRONTEND_VUE,
                ProjectType.FRONTEND_ANGULAR,
            }
        )

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract frontend entry points.

        Returns:
            List of Components, hooks, routes
        """
        entry_points = []

        # React
        entry_points.extend(self._extract_react_entry_points(project_path))

        # Vue
        entry_points.extend(self._extract_vue_entry_points(project_path))

        # Angular
        entry_points.extend(self._extract_angular_entry_points(project_path))

        return entry_points

    def _extract_react_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract React entry points (components, hooks, routes)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.tsx", "*.jsx"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Function components
            func_component_pattern = re.compile(
                r"export\s+(?:default\s+)?function\s+(\w+)\s*\("
            )
            for match in func_component_pattern.finditer(content):
                component_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Extract props
                props = self._extract_react_props(content, match.end())

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.COMPONENT,
                        name=component_name,
                        params=props,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="react",
                        metadata={"component_type": "function"},
                    )
                )

            # Arrow function components
            arrow_component_pattern = re.compile(
                r"(?:export\s+)?const\s+(\w+)\s*=\s*\(\s*[^)]*\s*\)\s*=>"
            )
            for match in arrow_component_pattern.finditer(content):
                component_name = match.group(1)

                # Check if it returns JSX
                if self._returns_jsx(content, match.end()):
                    line_num = content[: match.start()].count("\n") + 1

                    props = self._extract_react_props(content, match.start())

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.COMPONENT,
                            name=component_name,
                            params=props,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="react",
                            metadata={"component_type": "arrow"},
                        )
                    )

            # Custom hooks
            hook_pattern = re.compile(r"export\s+function\s+(use\w+)\s*\(")
            for match in hook_pattern.finditer(content):
                hook_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.HOOK,
                        name=hook_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="react",
                        metadata={"hook_type": "custom"},
                    )
                )

            # Routes (React Router)
            route_pattern = re.compile(r'<Route\s+path=["\']([^"\']+)["\']')
            for match in route_pattern.finditer(content):
                route_path = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.ROUTE,
                        name=route_path,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="react-router",
                        metadata={"route_type": "client"},
                    )
                )

        return entry_points

    def _extract_react_props(self, content: str, start_pos: int) -> list[Parameter]:
        """Extract props from React component signature."""
        props = []

        # Look for TypeScript props interface
        props_pattern = re.compile(r"interface\s+(\w+)Props\s*\{([^}]+)\}")
        for match in props_pattern.finditer(content[max(0, start_pos - 500) : start_pos + 500]):
            props_body = match.group(2)

            # Parse each prop
            prop_line_pattern = re.compile(r"(\w+)\??:\s*(\w+)")
            for prop_match in prop_line_pattern.finditer(props_body):
                prop_name, prop_type = prop_match.groups()
                props.append(
                    Parameter(
                        name=prop_name,
                        param_type="prop",
                        data_type=prop_type.lower(),
                        required="?" not in prop_match.group(0),
                    )
                )

        return props

    def _returns_jsx(self, content: str, start_pos: int) -> bool:
        """Check if function returns JSX."""
        # Look for return statement with JSX
        search_area = content[start_pos : start_pos + 600]
        return bool(re.search(r"return\s*\(?\s*<\w+", search_area))

    def _extract_vue_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract Vue entry points (components, composables)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.vue"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Component name from filename
            component_name = file_path.stem

            # Check for <script setup>
            if re.search(r"<script\s+setup", content):
                line_num = 1

                # Extract defineProps
                props = self._extract_vue_props(content)

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.COMPONENT,
                        name=component_name,
                        params=props,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="vue",
                        metadata={"component_type": "sfc", "setup": True},
                    )
                )

        # Composables (separate .ts/.js files)
        for file_path in walk_files(project_path, ["*.ts", "*.js"]):
            if "composables" not in str(file_path):
                continue

            content = read_file_safe(file_path)
            if not content:
                continue

            # Composable functions (use*)
            composable_pattern = re.compile(r"export\s+function\s+(use\w+)\s*\(")
            for match in composable_pattern.finditer(content):
                composable_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.COMPOSABLE,
                        name=composable_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="vue",
                        metadata={"composable_type": "function"},
                    )
                )

        return entry_points

    def _extract_vue_props(self, content: str) -> list[Parameter]:
        """Extract props from Vue component."""
        props = []

        # defineProps<{ ... }>()
        props_pattern = re.compile(r"defineProps<\{([^}]+)\}>")
        for match in props_pattern.finditer(content):
            props_body = match.group(1)

            # Parse each prop
            prop_line_pattern = re.compile(r"(\w+)\??:\s*(\w+)")
            for prop_match in prop_line_pattern.finditer(props_body):
                prop_name, prop_type = prop_match.groups()
                props.append(
                    Parameter(
                        name=prop_name,
                        param_type="prop",
                        data_type=prop_type.lower(),
                        required="?" not in prop_match.group(0),
                    )
                )

        return props

    def _extract_angular_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract Angular entry points (components, services)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.ts"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Components
            component_pattern = re.compile(
                r"@Component\s*\(\s*\{[^}]*selector:\s*['\"]([^'\"]+)['\"]"
            )
            for match in component_pattern.finditer(content):
                selector = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Extract @Input() properties
                inputs = self._extract_angular_inputs(content, match.end())

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.COMPONENT,
                        name=selector,
                        params=inputs,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="angular",
                        metadata={"component_type": "component"},
                    )
                )

        return entry_points

    def _extract_angular_inputs(self, content: str, start_pos: int) -> list[Parameter]:
        """Extract @Input() properties from Angular component."""
        inputs = []

        search_area = content[start_pos : start_pos + 1000]

        input_pattern = re.compile(r"@Input\(\)\s+(\w+):\s*(\w+)")
        for match in input_pattern.finditer(search_area):
            input_name, input_type = match.groups()
            inputs.append(
                Parameter(
                    name=input_name,
                    param_type="input",
                    data_type=input_type.lower(),
                    required=False,
                )
            )

        return inputs

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse frontend test files.

        Frontend tests typically use:
        - React: Jest, React Testing Library, Cypress
        - Vue: Vitest, Vue Test Utils
        - Angular: Jasmine, Karma
        Note: frontend test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate frontend test scenarios.

        For frontend components, scenarios include:
        - Props: Valid values, missing required, invalid types
        - State: Initial state, updates, edge cases
        - Events: User interactions, callbacks
        - Lifecycle: Mount, update, unmount
        - Routes: Navigation, parameters, guards
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.COMPONENT:
                # Happy path: Component with valid props
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="RENDER",
                        input_combination={
                            "props": {p.name: "valid_value" for p in entry_point.params}
                        },
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Render {entry_point.name} with valid props",
                    )
                )

                # Edge case: Missing optional props
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="RENDER",
                        input_combination={"props": {}},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Render {entry_point.name} without optional props",
                    )
                )

                # Error: Missing required props
                required_props = [p for p in entry_point.params if p.required]
                if required_props:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="RENDER",
                            input_combination={"props": {"missing": True}},
                            expected_output=1,
                            scenario_type="error",
                            description=f"Render {entry_point.name} without required props",
                        )
                    )

            elif entry_point.type == EntryPointType.ROUTE:
                # Route navigation scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="NAVIGATE",
                        input_combination={"params": {}},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Navigate to {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="NAVIGATE",
                        input_combination={"params": {"invalid": "data"}},
                        expected_output=1,
                        scenario_type="error",
                        description=f"Navigate to {entry_point.name} with invalid params",
                    )
                )

        return scenarios
