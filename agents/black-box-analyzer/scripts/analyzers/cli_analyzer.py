#!/usr/bin/env python3
"""CLI Analyzer for command-line applications.

Handles detection and analysis of CLI applications:
- Go: Cobra, urfave/cli, flag package
- Python: argparse, Click, Typer
- TypeScript: Commander.js, Yargs
- C#: CommandLineParser
- Java: Picocli
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import CLI_PATTERNS
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
    extract_line_number_from_pattern,
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_analyzer import BaseAnalyzer


class CLIAnalyzer(BaseAnalyzer):
    """Analyzer for CLI applications."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle CLI projects."""
        return ProjectType.CLI_APP in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract CLI commands, subcommands, and flags.

        Returns:
            List of EntryPoint objects representing CLI commands
        """
        entry_points = []

        # Detect CLI patterns in Go files
        entry_points.extend(self._extract_go_cli(project_path))

        # Detect CLI patterns in Python files
        entry_points.extend(self._extract_python_cli(project_path))

        # Detect CLI patterns in TypeScript/JavaScript files
        entry_points.extend(self._extract_typescript_cli(project_path))

        # Detect CLI patterns in C# files
        entry_points.extend(self._extract_csharp_cli(project_path))

        # Detect CLI patterns in Java files
        entry_points.extend(self._extract_java_cli(project_path))

        return entry_points

    def _extract_go_cli(self, project_path: Path) -> list[EntryPoint]:
        """Extract Go CLI commands (Cobra, flag, urfave/cli)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.go"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Cobra commands
            cobra_pattern = re.compile(
                r'&cobra\.Command\s*\{\s*Use:\s*"(\w+)"', re.MULTILINE
            )
            for match in cobra_pattern.finditer(content):
                command_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                # Extract flags for this command
                flags = self._extract_go_flags(content, match.start())

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_COMMAND,
                        name=command_name,
                        params=flags,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="cobra",
                        metadata={"language": "go"},
                    )
                )

            # Standard flag package
            flag_pattern = re.compile(r'flag\.(String|Int|Bool)\s*\(\s*"(\w+)"')
            for match in flag_pattern.finditer(content):
                flag_type, flag_name = match.groups()
                line_num = content[:match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_FLAG,
                        name=f"--{flag_name}",
                        params=[
                            Parameter(
                                name=flag_name,
                                param_type="flag",
                                data_type=flag_type.lower(),
                                required=False,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="flag",
                        metadata={"language": "go"},
                    )
                )

        return entry_points

    def _extract_go_flags(self, content: str, start_pos: int) -> list[Parameter]:
        """Extract flags defined after a Cobra command."""
        flags = []

        # Look for .Flags().StringVar, .Flags().IntVar, etc.
        flag_pattern = re.compile(
            r'\.Flags\(\)\.(String|Int|Bool)(?:Var)?P?\s*\(\s*[^,]*,\s*"(\w+)"'
        )

        # Only look in the next 500 characters (rough command scope)
        search_area = content[start_pos : start_pos + 500]

        for match in flag_pattern.finditer(search_area):
            flag_type, flag_name = match.groups()
            flags.append(
                Parameter(
                    name=flag_name,
                    param_type="flag",
                    data_type=flag_type.lower(),
                    required=False,
                )
            )

        return flags

    def _extract_python_cli(self, project_path: Path) -> list[EntryPoint]:
        """Extract Python CLI commands (argparse, Click, Typer)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Click commands — two-pass: find decorator, then nearest following def
            # Handles @click.command(), @click.command(name="x"), bare @click.command
            click_decorator_pattern = re.compile(r"@click\.(command|group)\s*(\([^)]*\))?")
            click_def_pattern = re.compile(r"def\s+(\w+)\s*\(")
            for dec_match in click_decorator_pattern.finditer(content):
                cmd_type = dec_match.group(1)
                window = content[dec_match.end():dec_match.end() + 300]
                def_match = click_def_pattern.search(window)
                if not def_match:
                    continue
                cmd_name = def_match.group(1)
                dec_start = dec_match.start()
                line_num = content[:dec_start].count("\n") + 1

                # Extract click options
                options = self._extract_click_options(content, dec_start)

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_COMMAND,
                        name=cmd_name,
                        params=options,
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="click",
                        metadata={"language": "python", "type": cmd_type},
                    )
                )

            # Argparse
            argparse_pattern = re.compile(
                r'add_argument\s*\(\s*["\']--?(\w+)["\']'
            )
            for match in argparse_pattern.finditer(content):
                arg_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_FLAG,
                        name=f"--{arg_name}",
                        params=[
                            Parameter(
                                name=arg_name,
                                param_type="flag",
                                data_type="string",
                                required=False,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="argparse",
                        metadata={"language": "python"},
                    )
                )

        return entry_points

    def _extract_click_options(self, content: str, start_pos: int) -> list[Parameter]:
        """Extract @click.option decorators before a command."""
        options = []

        # Look backwards for @click.option decorators
        search_area = content[max(0, start_pos - 500) : start_pos]

        option_pattern = re.compile(r'@click\.option\s*\(\s*["\']--?(\w+)["\']')
        for match in option_pattern.finditer(search_area):
            option_name = match.group(1)
            options.append(
                Parameter(
                    name=option_name,
                    param_type="flag",
                    data_type="string",
                    required=False,
                )
            )

        return options

    def _extract_typescript_cli(self, project_path: Path) -> list[EntryPoint]:
        """Extract TypeScript/JavaScript CLI commands (Commander.js, Yargs)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.ts", "*.js"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Commander.js commands
            commander_pattern = re.compile(
                r'program\.command\s*\(\s*["\'](\w+)["\']'
            )
            for match in commander_pattern.finditer(content):
                command_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_COMMAND,
                        name=command_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="commander",
                        metadata={"language": "typescript"},
                    )
                )

        return entry_points

    def _extract_csharp_cli(self, project_path: Path) -> list[EntryPoint]:
        """Extract C# CLI commands (CommandLineParser)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.cs"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # CommandLineParser [Option] attributes
            option_pattern = re.compile(r'\[Option\s*\(\s*["\'](\w+)["\']')
            for match in option_pattern.finditer(content):
                option_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_FLAG,
                        name=f"--{option_name}",
                        params=[
                            Parameter(
                                name=option_name,
                                param_type="flag",
                                data_type="string",
                                required=False,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="commandlineparser",
                        metadata={"language": "csharp"},
                    )
                )

        return entry_points

    def _extract_java_cli(self, project_path: Path) -> list[EntryPoint]:
        """Extract Java CLI commands (Picocli)."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.java"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Picocli @Command annotation
            command_pattern = re.compile(r'@Command\s*\(\s*name\s*=\s*"(\w+)"')
            for match in command_pattern.finditer(content):
                command_name = match.group(1)
                line_num = content[:match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.CLI_COMMAND,
                        name=command_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="picocli",
                        metadata={"language": "java"},
                    )
                )

        return entry_points

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse CLI test files.

        CLI tests typically invoke commands with various flags.
        Note: CLI test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate CLI test scenarios.

        For CLI commands, scenarios include:
        - Happy path: Valid flags with correct values
        - Error: Missing required flags
        - Edge case: Invalid flag values
        - Security: Command injection attempts
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type == EntryPointType.CLI_COMMAND:
                # Happy path: Command with valid flags
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="CLI",  # Not HTTP, but needed for Scenario model
                        input_combination={
                            "flags": [f"--{p.name}=valid" for p in entry_point.params]
                        },
                        expected_output=0,  # Exit code 0
                        scenario_type="happy_path",
                        description=f"Valid execution of '{entry_point.name}' with all flags",
                    )
                )

                # Error: Missing required flag
                if any(p.required for p in entry_point.params):
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="CLI",
                            input_combination={"flags": []},
                            expected_output=1,  # Exit code 1
                            scenario_type="error",
                            description=f"Missing required flags for '{entry_point.name}'",
                        )
                    )

                # Edge case: Invalid flag value
                for param in entry_point.params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="CLI",
                            input_combination={
                                "flags": [f"--{param.name}=<invalid>"]
                            },
                            expected_output=1,
                            scenario_type="edge_case",
                            description=f"Invalid value for flag '{param.name}'",
                        )
                    )

                # Security: Command injection
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="CLI",
                        input_combination={
                            "flags": ["--input='; rm -rf /'"]
                        },
                        expected_output=1,
                        scenario_type="security",
                        description=f"Command injection attempt on '{entry_point.name}'",
                    )
                )

        return scenarios
