#!/usr/bin/env python3
"""Desktop Analyzer for Windows/Mac/Linux desktop applications.

Handles detection and analysis of desktop apps:
- Windows: WPF, WinForms, Avalonia
- macOS: AppKit, SwiftUI
- Linux: Qt, GTK
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import DESKTOP_PATTERNS
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


class DesktopAnalyzer(BaseAnalyzer):
    """Analyzer for desktop applications (Windows/Mac/Linux)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle desktop projects."""
        return any(
            pt in project_info.project_types
            for pt in {
                ProjectType.DESKTOP_WINDOWS,
                ProjectType.DESKTOP_MAC,
                ProjectType.DESKTOP_LINUX,
            }
        )

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract desktop UI entry points.

        Returns:
            List of Windows, Dialogs, event handlers
        """
        entry_points = []

        # Windows (WPF, WinForms)
        entry_points.extend(self._extract_windows_entry_points(project_path))

        # macOS (AppKit)
        entry_points.extend(self._extract_macos_entry_points(project_path))

        # Linux (Qt, GTK)
        entry_points.extend(self._extract_linux_entry_points(project_path))

        return entry_points

    def _extract_windows_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract Windows desktop entry points (WPF, WinForms)."""
        entry_points = []

        # WPF XAML files
        for file_path in walk_files(project_path, ["*.xaml"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Windows
            window_pattern = re.compile(r'<Window[^>]+x:Class="([^"]+)"')
            for match in window_pattern.finditer(content):
                window_class = match.group(1)
                window_name = window_class.split(".")[-1]
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.WINDOW,
                        name=window_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="wpf",
                        metadata={"class": window_class},
                    )
                )

        # WPF/WinForms C# code-behind
        for file_path in walk_files(project_path, ["*.cs"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Click event handlers
            click_pattern = re.compile(r"void\s+(\w+)_Click\s*\(")
            for match in click_pattern.finditer(content):
                handler_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.EVENT_HANDLER,
                        name=f"{handler_name}_Click",
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="wpf",
                        metadata={"event_type": "click"},
                    )
                )

            # WinForms Form classes
            form_pattern = re.compile(r"class\s+(\w+)\s*:\s*Form")
            for match in form_pattern.finditer(content):
                form_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.WINDOW,
                        name=form_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="winforms",
                        metadata={"component_type": "form"},
                    )
                )

        return entry_points

    def _extract_macos_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract macOS desktop entry points (AppKit)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.swift", "*.m"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # NSWindowController
            window_pattern = re.compile(r"class\s+(\w+)\s*:\s*NSWindowController")
            for match in window_pattern.finditer(content):
                window_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.WINDOW,
                        name=window_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="appkit",
                        metadata={"component_type": "window_controller"},
                    )
                )

            # @IBAction methods
            action_pattern = re.compile(r"@IBAction\s+func\s+(\w+)")
            for match in action_pattern.finditer(content):
                action_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.EVENT_HANDLER,
                        name=action_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="appkit",
                        metadata={"handler_type": "ibaction"},
                    )
                )

        return entry_points

    def _extract_linux_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract Linux desktop entry points (Qt, GTK)."""
        entry_points = []

        # Qt C++ files
        for file_path in walk_files(project_path, ["*.cpp", "*.h"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # QMainWindow
            window_pattern = re.compile(r"class\s+(\w+)\s*:\s*public\s+QMainWindow")
            for match in window_pattern.finditer(content):
                window_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.WINDOW,
                        name=window_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="qt",
                        metadata={"component_type": "main_window"},
                    )
                )

            # Qt slots (event handlers)
            slot_pattern = re.compile(r"void\s+(\w+)\s*\(\s*\)\s*;")
            for match in slot_pattern.finditer(content):
                slot_name = match.group(1)

                # Check if it's a slot
                if "slots:" in content[max(0, match.start() - 1000) : match.start()]:
                    line_num = content[: match.start()].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.EVENT_HANDLER,
                            name=slot_name,
                            params=[],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="qt",
                            metadata={"handler_type": "slot"},
                        )
                    )

        # GTK (Python bindings)
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # GtkWindow
            gtk_window_pattern = re.compile(r"class\s+(\w+)\s*\(.*Gtk\.Window")
            for match in gtk_window_pattern.finditer(content):
                window_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.WINDOW,
                        name=window_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="gtk",
                        metadata={"component_type": "window"},
                    )
                )

        return entry_points

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse desktop test files.

        Desktop tests typically use:
        - Windows: MSTest, xUnit with UI automation
        - macOS: XCTest with UI testing
        - Linux: Qt Test, GTest
        Note: desktop test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate desktop test scenarios.

        For desktop apps, scenarios include:
        - Window lifecycle: Open, close, minimize, maximize
        - UI interactions: Button clicks, menu actions, keyboard shortcuts
        - Data binding: Property changes, validation
        - Dialogs: Modal, modeless, confirmation
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.WINDOW:
                # Window lifecycle scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WINDOW",
                        input_combination={"action": "open"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Open window {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WINDOW",
                        input_combination={"action": "close"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Close window {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WINDOW",
                        input_combination={"action": "minimize"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Minimize window {entry_point.name}",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="WINDOW",
                        input_combination={"action": "maximize"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Maximize window {entry_point.name}",
                    )
                )

            elif entry_point.type == EntryPointType.EVENT_HANDLER:
                # Event handler scenarios
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="EVENT",
                        input_combination={"trigger": "click"},
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Trigger {entry_point.name} event",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="EVENT",
                        input_combination={"trigger": "double_click"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Double-trigger {entry_point.name} event",
                    )
                )

                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="EVENT",
                        input_combination={"trigger": "rapid_clicks"},
                        expected_output=0,
                        scenario_type="edge_case",
                        description=f"Rapid clicks on {entry_point.name}",
                    )
                )

        return scenarios
