#!/usr/bin/env python3
"""Serverless Analyzer for AWS Lambda, Azure Functions, Google Cloud Functions.

Handles detection and analysis of serverless function entry points:
- AWS Lambda (Python, Node.js, Go handlers)
- Azure Functions (Python, C#, Node.js)
- Google Cloud Functions (Python, Node.js)
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.constants import SERVERLESS_PATTERNS
from common.models import (
    EntryPoint,
    EntryPointType,
    Parameter,
    ProjectInfo,
    ProjectType,
    TestCase,
)
from common.utils import (
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_event_driven_analyzer import BaseEventDrivenAnalyzer


class ServerlessAnalyzer(BaseEventDrivenAnalyzer):
    """Analyzer for serverless functions (Lambda, Azure Functions, Cloud Functions)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle serverless projects."""
        return ProjectType.SERVERLESS in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract serverless function handlers.

        Returns:
            List of Lambda handlers, Azure Functions, Cloud Functions
        """
        entry_points = []

        # AWS Lambda handlers
        entry_points.extend(self._extract_lambda_handlers(project_path))

        # Azure Functions
        entry_points.extend(self._extract_azure_functions(project_path))

        # Google Cloud Functions
        entry_points.extend(self._extract_cloud_functions(project_path))

        return entry_points

    def _extract_lambda_handlers(self, project_path: Path) -> list[EntryPoint]:
        """Extract AWS Lambda handlers."""
        entry_points = []

        # Python Lambda handlers
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: def lambda_handler(event, context):
            lambda_pattern = SERVERLESS_PATTERNS["aws_lambda_python"]
            for match in lambda_pattern.finditer(content):
                handler_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.LAMBDA_HANDLER,
                        name=handler_name,
                        params=[
                            Parameter(
                                name="event",
                                param_type="lambda_event",
                                data_type="dict",
                                required=True,
                            ),
                            Parameter(
                                name="context",
                                param_type="lambda_context",
                                data_type="LambdaContext",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="aws_lambda",
                        metadata={"runtime": "python", "handler_type": "function"},
                    )
                )

        # Node.js Lambda handlers
        for file_path in walk_files(project_path, ["*.js", "*.ts"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: exports.handler = async (event, context) => { }
            node_lambda_pattern = SERVERLESS_PATTERNS["aws_lambda_node"]
            for match in node_lambda_pattern.finditer(content):
                handler_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.LAMBDA_HANDLER,
                        name=handler_name,
                        params=[
                            Parameter(
                                name="event",
                                param_type="lambda_event",
                                data_type="object",
                                required=True,
                            ),
                            Parameter(
                                name="context",
                                param_type="lambda_context",
                                data_type="Context",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="aws_lambda",
                        metadata={"runtime": "nodejs", "handler_type": "export"},
                    )
                )

        # Go Lambda handlers
        for file_path in walk_files(project_path, ["*.go"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: func handler(ctx context.Context, event events.XXX)
            go_lambda_pattern = SERVERLESS_PATTERNS["aws_lambda_go"]
            for match in go_lambda_pattern.finditer(content):
                # Use capture group 1 (function name) — avoid fragile string surgery on group(0)
                handler_name = match.group(1) if match.lastindex and match.lastindex >= 1 else "handler"
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.LAMBDA_HANDLER,
                        name=handler_name,
                        params=[
                            Parameter(
                                name="ctx",
                                param_type="lambda_context",
                                data_type="context.Context",
                                required=True,
                            ),
                            Parameter(
                                name="event",
                                param_type="lambda_event",
                                data_type="events.Event",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="aws_lambda",
                        metadata={"runtime": "go", "handler_type": "function"},
                    )
                )

        return entry_points

    def _extract_azure_functions(self, project_path: Path) -> list[EntryPoint]:
        """Extract Azure Functions."""
        entry_points = []

        # Python Azure Functions (decorators)
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: @app.route(...) or @app.function_name(...)
            azure_pattern = SERVERLESS_PATTERNS["azure_function"]
            for match in azure_pattern.finditer(content):
                # Bound search to 300 chars after decorator to avoid picking up unrelated funcs
                window_start = match.end()
                window = content[window_start:window_start + 300]
                func_pattern = re.compile(r"def\s+(\w+)\s*\(", re.MULTILINE)
                func_match = func_pattern.search(window)
                if func_match:
                    func_name = func_match.group(1)
                    abs_pos = window_start + func_match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.FUNCTION_HANDLER,
                            name=func_name,
                            params=[
                                Parameter(
                                    name="req",
                                    param_type="http_request",
                                    data_type="HttpRequest",
                                    required=True,
                                )
                            ],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="azure_functions",
                            metadata={"runtime": "python", "trigger": "http"},
                        )
                    )

        # C# Azure Functions (attributes)
        for file_path in walk_files(project_path, ["*.cs"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: [FunctionName("FunctionName")]
            func_name_pattern = re.compile(r'\[FunctionName\s*\(\s*"([^"]+)"\s*\)\]')
            for match in func_name_pattern.finditer(content):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.FUNCTION_HANDLER,
                        name=func_name,
                        params=[],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="azure_functions",
                        metadata={"runtime": "csharp", "trigger": "http"},
                    )
                )

        return entry_points

    def _extract_cloud_functions(self, project_path: Path) -> list[EntryPoint]:
        """Extract Google Cloud Functions."""
        entry_points = []

        # Python Cloud Functions (decorators)
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: @functions_framework.http
            gcp_pattern = SERVERLESS_PATTERNS["gcp_function"]
            for match in gcp_pattern.finditer(content):
                # Bound search to 300 chars after decorator
                window_start = match.end()
                window = content[window_start:window_start + 300]
                func_pattern = re.compile(r"def\s+(\w+)\s*\(", re.MULTILINE)
                func_match = func_pattern.search(window)
                if func_match:
                    func_name = func_match.group(1)
                    abs_pos = window_start + func_match.start()
                    line_num = content[:abs_pos].count("\n") + 1

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.FUNCTION_HANDLER,
                            name=func_name,
                            params=[
                                Parameter(
                                    name="request",
                                    param_type="http_request",
                                    data_type="Request",
                                    required=True,
                                )
                            ],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="google_cloud_functions",
                            metadata={"runtime": "python", "trigger": "http"},
                        )
                    )

        # Node.js Cloud Functions
        for file_path in walk_files(project_path, ["*.js", "*.ts"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: exports.functionName = (req, res) => { }
            node_gcp_pattern = re.compile(
                r"exports\.(\w+)\s*=\s*\(req,\s*res\)\s*=>"
            )
            for match in node_gcp_pattern.finditer(content):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.FUNCTION_HANDLER,
                        name=func_name,
                        params=[
                            Parameter(
                                name="req",
                                param_type="http_request",
                                data_type="Request",
                                required=True,
                            ),
                            Parameter(
                                name="res",
                                param_type="http_response",
                                data_type="Response",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="google_cloud_functions",
                        metadata={"runtime": "nodejs", "trigger": "http"},
                    )
                )

        return entry_points

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse serverless function test files.

        Serverless tests typically:
        - Mock event payloads (Lambda events, HTTP requests)
        - Test cold start behavior
        - Validate response format
        - Check timeout handling
        Note: serverless test parsing tracked in #3
        """
        return []
