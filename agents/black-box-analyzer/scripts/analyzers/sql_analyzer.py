#!/usr/bin/env python3
"""SQL Analyzer for database projects.

Handles detection and analysis of SQL projects:
- Stored procedures
- Functions
- Triggers
- Migrations
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import SQL_PATTERNS
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


class SQLAnalyzer(BaseAnalyzer):
    """Analyzer for SQL projects (stored procedures, triggers, functions)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle SQL projects."""
        return ProjectType.SQL_PROJECT in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract SQL entry points.

        Returns:
            List of stored procedures, functions, triggers
        """
        entry_points = []

        for file_path in walk_files(project_path, ["*.sql"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Stored procedures
            entry_points.extend(
                self._extract_stored_procedures(content, file_path, project_path)
            )

            # Functions
            entry_points.extend(
                self._extract_functions(content, file_path, project_path)
            )

            # Triggers
            entry_points.extend(
                self._extract_triggers(content, file_path, project_path)
            )

        return entry_points

    def _extract_stored_procedures(
        self, content: str, file_path: Path, project_path: Path
    ) -> list[EntryPoint]:
        """Extract stored procedures."""
        procedures = []

        # PostgreSQL / SQL Server procedures
        proc_pattern = re.compile(
            r"CREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?(?:PROCEDURE|PROC)\s+(\w+)\s*\(([^)]*)\)",
            re.IGNORECASE,
        )

        for match in proc_pattern.finditer(content):
            proc_name = match.group(1)
            params_str = match.group(2)
            line_num = content[: match.start()].count("\n") + 1

            # Parse parameters
            params = self._parse_sql_params(params_str)

            procedures.append(
                EntryPoint(
                    type=EntryPointType.STORED_PROCEDURE,
                    name=proc_name,
                    params=params,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework="sql",
                    metadata={"object_type": "procedure"},
                )
            )

        return procedures

    def _extract_functions(
        self, content: str, file_path: Path, project_path: Path
    ) -> list[EntryPoint]:
        """Extract SQL functions."""
        functions = []

        # PostgreSQL / SQL Server functions
        func_pattern = re.compile(
            r"CREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?FUNCTION\s+(\w+)\s*\(([^)]*)\)",
            re.IGNORECASE,
        )

        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            params_str = match.group(2)
            line_num = content[: match.start()].count("\n") + 1

            # Parse parameters
            params = self._parse_sql_params(params_str)

            functions.append(
                EntryPoint(
                    type=EntryPointType.SQL_FUNCTION,
                    name=func_name,
                    params=params,
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework="sql",
                    metadata={"object_type": "function"},
                )
            )

        return functions

    def _extract_triggers(
        self, content: str, file_path: Path, project_path: Path
    ) -> list[EntryPoint]:
        """Extract SQL triggers."""
        triggers = []

        # PostgreSQL / SQL Server triggers
        trigger_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(\w+)",
            re.IGNORECASE,
        )

        for match in trigger_pattern.finditer(content):
            trigger_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            triggers.append(
                EntryPoint(
                    type=EntryPointType.SQL_TRIGGER,
                    name=trigger_name,
                    params=[],
                    file_path=format_path_relative(file_path, project_path),
                    line_number=line_num,
                    framework="sql",
                    metadata={"object_type": "trigger"},
                )
            )

        return triggers

    def _parse_sql_params(self, params_str: str) -> list[Parameter]:
        """Parse SQL parameters."""
        params = []

        if not params_str.strip():
            return params

        # Split by comma
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Parse: @name TYPE or name TYPE or IN name TYPE
            parts = re.match(
                r"(?:IN|OUT|INOUT)?\s*[@]?(\w+)\s+(\w+)",
                param,
                re.IGNORECASE,
            )
            if parts:
                name = parts.group(1)
                param_type = parts.group(2)

                params.append(
                    Parameter(
                        name=name,
                        param_type="sql_param",
                        data_type=param_type.lower(),
                        required=True,
                    )
                )

        return params

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse SQL test files.

        SQL tests typically:
        - Use frameworks like pgTAP, tSQLt, utPLSQL
        - Test procedures with various inputs
        - Validate constraints and triggers
        Note: SQL test parsing tracked in #3
        """
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate SQL test scenarios.

        For SQL objects, scenarios include:
        - Procedures/Functions: Valid params, NULL values, constraint violations
        - Triggers: INSERT, UPDATE, DELETE operations
        - Edge cases: Empty strings, negative numbers, max values
        - Security: SQL injection (already prevented by parameterization)
        """
        scenarios = []

        for entry_point in entry_points:
            if entry_point.type in {
                EntryPointType.STORED_PROCEDURE,
                EntryPointType.SQL_FUNCTION,
            }:
                # Happy path: Valid parameters
                scenarios.append(
                    Scenario(
                        endpoint=entry_point.name,
                        method="EXECUTE",
                        input_combination={
                            "params": {p.name: "valid_value" for p in entry_point.params}
                        },
                        expected_output=0,
                        scenario_type="happy_path",
                        description=f"Execute {entry_point.name} with valid params",
                    )
                )

                # Edge case: NULL values
                for param in entry_point.params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="EXECUTE",
                            input_combination={
                                "params": {param.name: None}
                            },
                            expected_output=0,
                            scenario_type="edge_case",
                            description=f"{entry_point.name} with NULL {param.name}",
                        )
                    )

                # Edge case: Empty strings (for VARCHAR params)
                string_params = [p for p in entry_point.params if "char" in p.data_type.lower()]
                for param in string_params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="EXECUTE",
                            input_combination={
                                "params": {param.name: ""}
                            },
                            expected_output=0,
                            scenario_type="edge_case",
                            description=f"{entry_point.name} with empty {param.name}",
                        )
                    )

                # Edge case: Negative numbers (for INT params)
                int_params = [p for p in entry_point.params if "int" in p.data_type.lower()]
                for param in int_params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="EXECUTE",
                            input_combination={
                                "params": {param.name: -1}
                            },
                            expected_output=0,
                            scenario_type="edge_case",
                            description=f"{entry_point.name} with negative {param.name}",
                        )
                    )

                # Error: Missing required parameter
                if entry_point.params:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method="EXECUTE",
                            input_combination={"params": {}},
                            expected_output=1,
                            scenario_type="error",
                            description=f"{entry_point.name} without required params",
                        )
                    )

            elif entry_point.type == EntryPointType.SQL_TRIGGER:
                # Trigger scenarios (test INSERT, UPDATE, DELETE)
                for operation in ["INSERT", "UPDATE", "DELETE"]:
                    scenarios.append(
                        Scenario(
                            endpoint=entry_point.name,
                            method=operation,
                            input_combination={"operation": operation.lower()},
                            expected_output=0,
                            scenario_type="happy_path",
                            description=f"Trigger {entry_point.name} on {operation}",
                        )
                    )

        return scenarios
