#!/usr/bin/env python3
"""Mobile Analyzer for Android and iOS applications.

Handles detection and analysis of mobile apps:
- Android: Activities, Fragments, ViewModels, Jetpack Compose
- iOS: ViewControllers, Views, SwiftUI
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import MOBILE_PATTERNS
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


class MobileAnalyzer(BaseAnalyzer):
    """Analyzer for mobile applications (Android/iOS)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle mobile projects."""
        return (
            ProjectType.ANDROID_APP in project_info.project_types
            or ProjectType.IOS_APP in project_info.project_types
        )

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract mobile UI entry points.

        Returns:
            List of Activities, Fragments, ViewControllers, lifecycle methods
        """
        entry_points = []

        # Detect Android entry points
        entry_points.extend(self._extract_android_entry_points(project_path))

        # Detect iOS entry points
        entry_points.extend(self._extract_ios_entry_points(project_path))

        return entry_points

    def _extract_android_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract Android entry points (Activities, Fragments, Compose)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.kt", "*.java"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Activities
            activity_pattern = re.compile(
                r"class\s+(\w+)\s*:\s*(?:AppCompat)?Activity"
            )
            for match in activity_pattern.finditer(content):
                activity_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.ACTIVITY,
                        name=activity_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="android",
                        metadata={"component_type": "activity"},
                    )
                )

                # Extract lifecycle methods within this Activity
                entry_points.extend(
                    self._extract_android_lifecycle(
                        content, activity_name, file_path, project_path, match.end()
                    )
                )

            # Fragments
            fragment_pattern = re.compile(r"class\s+(\w+)\s*:\s*Fragment")
            for match in fragment_pattern.finditer(content):
                fragment_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.FRAGMENT,
                        name=fragment_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="android",
                        metadata={"component_type": "fragment"},
                    )
                )

            # Jetpack Compose @Composable functions
            composable_pattern = re.compile(r"@Composable\s+fun\s+(\w+)")
            for match in composable_pattern.finditer(content):
                composable_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.COMPONENT,
                        name=composable_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="compose",
                        metadata={"component_type": "composable"},
                    )
                )

        return entry_points

    def _extract_android_lifecycle(
        self,
        content: str,
        parent_name: str,
        file_path: Path,
        project_path: Path,
        start_pos: int,
    ) -> list[EntryPoint]:
        """Extract Android lifecycle methods."""
        lifecycle_methods = []

        lifecycle_pattern = re.compile(
            r"override\s+fun\s+(onCreate|onStart|onResume|onPause|onStop|onDestroy)"
        )

        # Bound search to end of this class body — stop at next class declaration
        next_class = re.search(r"\nclass\s+", content[start_pos:])
        end_pos = start_pos + next_class.start() if next_class else len(content)
        search_area = content[start_pos:end_pos]

        for match in lifecycle_pattern.finditer(search_area):
            method_name = match.group(1)
            line_num = content[: start_pos + match.start()].count("\n") + 1

            lifecycle_methods.append(
                EntryPoint(
                    type=EntryPointType.LIFECYCLE_METHOD,
                    name=f"{parent_name}.{method_name}",
                    params=[],
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework="android",
                    metadata={
                        "parent": parent_name,
                        "lifecycle_stage": method_name,
                    },
                )
            )

        return lifecycle_methods

    def _extract_ios_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract iOS entry points (ViewControllers, SwiftUI Views)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.swift", "*.m"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # UIViewControllers
            vc_pattern = re.compile(r"class\s+(\w+)\s*:\s*UIViewController")
            for match in vc_pattern.finditer(content):
                vc_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.VIEW_CONTROLLER,
                        name=vc_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="uikit",
                        metadata={"component_type": "view_controller"},
                    )
                )

                # Extract lifecycle methods
                entry_points.extend(
                    self._extract_ios_lifecycle(
                        content, vc_name, file_path, project_path, match.end()
                    )
                )

            # SwiftUI Views
            swiftui_pattern = re.compile(r"struct\s+(\w+)\s*:\s*View")
            for match in swiftui_pattern.finditer(content):
                view_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.SWIFTUI_VIEW,
                        name=view_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="swiftui",
                        metadata={"component_type": "swiftui_view"},
                    )
                )

            # @IBAction methods
            ibaction_pattern = re.compile(r"@IBAction\s+func\s+(\w+)")
            for match in ibaction_pattern.finditer(content):
                action_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.UI_HANDLER,
                        name=action_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="uikit",
                        metadata={"handler_type": "ibaction"},
                    )
                )

        return entry_points

    def _extract_ios_lifecycle(
        self,
        content: str,
        parent_name: str,
        file_path: Path,
        project_path: Path,
        start_pos: int,
    ) -> list[EntryPoint]:
        """Extract iOS lifecycle methods."""
        lifecycle_methods = []

        lifecycle_pattern = re.compile(
            r"override\s+func\s+(viewDidLoad|viewWillAppear|viewDidAppear|viewWillDisappear|viewDidDisappear)"
        )

        # Bound search to end of this class body — stop at next class declaration
        next_class = re.search(r"\nclass\s+", content[start_pos:])
        end_pos = start_pos + next_class.start() if next_class else len(content)
        search_area = content[start_pos:end_pos]

        for match in lifecycle_pattern.finditer(search_area):
            method_name = match.group(1)
            line_num = content[: start_pos + match.start()].count("\n") + 1

            lifecycle_methods.append(
                EntryPoint(
                    type=EntryPointType.LIFECYCLE_METHOD,
                    name=f"{parent_name}.{method_name}",
                    params=[],
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework="uikit",
                    metadata={
                        "parent": parent_name,
                        "lifecycle_stage": method_name,
                    },
                )
            )

        return lifecycle_methods

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse mobile test files.

        Mobile tests typically use:
        - Android: Espresso, Robolectric, JUnit
        - iOS: XCTest, XCUITest
        Note: mobile test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate mobile test scenarios.

        For mobile apps, scenarios include:
        - Lifecycle: onCreate → onStart → onResume → onPause → onStop → onDestroy
        - UI interactions: Tap, swipe, long press
        - State management: Rotation, background/foreground
        - Navigation: Back button, deep links
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.LIFECYCLE_METHOD:
                # Lifecycle scenarios
                lifecycle_stage = entry_point.metadata.get("lifecycle_stage", "unknown")

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="LIFECYCLE",
                        input_combination={"state": lifecycle_stage},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Normal execution of {lifecycle_stage}",
                    )
                )

                # Edge case: Rapid lifecycle transitions
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="LIFECYCLE",
                        input_combination={"state": f"{lifecycle_stage}_rapid"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Rapid {lifecycle_stage} transitions",
                    )
                )

            elif entry_point.type in {
                EntryPointType.ACTIVITY,
                EntryPointType.FRAGMENT,
                EntryPointType.VIEW_CONTROLLER,
                EntryPointType.SWIFTUI_VIEW,
            }:
                # Component initialization scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="INIT",
                        input_combination={"init_type": "normal"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Normal initialization of {entry_point.name}",
                    )
                )

                # Edge case: Initialization with saved state
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="INIT",
                        input_combination={"init_type": "restore_state"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Restore state for {entry_point.name}",
                    )
                )

            elif entry_point.type == EntryPointType.UI_HANDLER:
                # UI interaction scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="INTERACTION",
                        input_combination={"gesture": "tap"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Tap on {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="INTERACTION",
                        input_combination={"gesture": "long_press"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Long press on {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="INTERACTION",
                        input_combination={"gesture": "double_tap"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Double tap on {entry_point.name}",
                    )
                )

        return scenarios
