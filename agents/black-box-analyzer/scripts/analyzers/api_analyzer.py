#!/usr/bin/env python3
"""API Analyzer for REST/GraphQL/gRPC projects.

Handles detection and analysis of API-based projects:
- REST APIs (Go/gin, TypeScript/Express, C#/ASP.NET, Python/FastAPI, Java/Spring)
- GraphQL APIs (Apollo Server, HotChocolate)
- gRPC APIs (gRPC-Go, gRPC-Core)
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.constants import (
    DEFAULT_RESPONSE_CODES,
    ENDPOINT_PATTERNS,
)
from common.models import (
    Endpoint,
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    Parameter,
    ProjectInfo,
    ProjectType,
    Scenario,
    TestCase,
)
from common.utils import (
    extract_line_number_from_pattern,
    extract_params_from_path,
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_analyzer import BaseAnalyzer


class APIAnalyzer(BaseAnalyzer):
    """Analyzer for API projects (REST/GraphQL/gRPC)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle the project.

        Returns True if project contains any API type.
        """
        api_types = {
            ProjectType.REST_API,
            ProjectType.GRAPHQL_API,
            ProjectType.GRPC_API,
        }
        return any(pt in api_types for pt in project_info.project_types)

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract API endpoints from project.

        Returns:
            List of EntryPoint objects (converted from Endpoint for compatibility)
        """
        # Extract classic endpoints (kept from existing logic)
        endpoints = self._extract_endpoints(project_path)

        # Convert Endpoint → EntryPoint (universal format)
        entry_points = []
        for endpoint in endpoints:
            entry_points.append(
                EntryPoint(
                    type=EntryPointType.HTTP_ENDPOINT,
                    name=f"{endpoint.method.value} {endpoint.path}",
                    params=endpoint.params,
                    file_path=endpoint.file_path,
                    line_number=endpoint.line_number,
                    framework=endpoint.framework,
                    metadata={
                        "method": endpoint.method.value,
                        "path": endpoint.path,
                        "response_codes": endpoint.response_codes,
                        "handler_name": endpoint.handler_name,
                    },
                )
            )

        return entry_points

    def _extract_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract endpoints using existing logic (reused from extract_api_endpoints.py).

        This method reuses the proven extraction logic.
        """
        endpoints = []

        # Detect which extractors to use based on files present
        if list(walk_files(project_path, ["*.go"])):
            endpoints.extend(self._extract_go_endpoints(project_path))

        if list(walk_files(project_path, ["*.ts", "*.js"])):
            endpoints.extend(self._extract_typescript_endpoints(project_path))

        if list(walk_files(project_path, ["*.cs"])):
            endpoints.extend(self._extract_csharp_endpoints(project_path))

        if list(walk_files(project_path, ["*.py"])):
            endpoints.extend(self._extract_python_endpoints(project_path))

        if list(walk_files(project_path, ["*.java"])):
            endpoints.extend(self._extract_java_endpoints(project_path))

        return endpoints

    def _extract_go_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract Go endpoints (gin, echo, fiber, chi, mux)."""
        endpoints = []

        for file_path in walk_files(project_path, ["*.go"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            for pattern_name, pattern in ENDPOINT_PATTERNS.items():
                if not pattern_name.startswith("go_"):
                    continue

                matches = pattern.findall(content)
                for match in matches:
                    if pattern_name == "go_mux":
                        path, method = match
                    else:
                        method, path = match

                    method = method.upper()

                    try:
                        http_method = HTTPMethod(method)
                    except ValueError:
                        continue

                    params = extract_params_from_path(path)
                    response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])
                    line_num = extract_line_number_from_pattern(content, path)

                    endpoints.append(
                        Endpoint(
                            path=path,
                            method=http_method,
                            params=params,
                            response_codes=response_codes,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework=pattern_name.replace("go_", ""),
                        )
                    )

        return endpoints

    def _extract_typescript_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract TypeScript/JavaScript endpoints (Express, NestJS, Fastify)."""
        endpoints = []

        for file_path in walk_files(project_path, ["*.ts", "*.js"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            for pattern_name, pattern in ENDPOINT_PATTERNS.items():
                if not pattern_name.startswith("ts_"):
                    continue

                matches = pattern.findall(content)
                for match in matches:
                    method, path = match
                    method = method.upper()

                    try:
                        http_method = HTTPMethod(method)
                    except ValueError:
                        continue

                    params = extract_params_from_path(path)
                    response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])
                    line_num = extract_line_number_from_pattern(content, path)

                    endpoints.append(
                        Endpoint(
                            path=path,
                            method=http_method,
                            params=params,
                            response_codes=response_codes,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework=pattern_name.replace("ts_", ""),
                        )
                    )

        return endpoints

    def _extract_csharp_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract C# endpoints (ASP.NET attributes + minimal APIs)."""
        endpoints = []

        for file_path in walk_files(project_path, ["*.cs"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            for pattern_name, pattern in ENDPOINT_PATTERNS.items():
                if not pattern_name.startswith("cs_"):
                    continue

                matches = pattern.findall(content)
                for match in matches:
                    method, path = match

                    if not path:
                        path = "/"

                    method_map = {
                        "Get": "GET",
                        "Post": "POST",
                        "Put": "PUT",
                        "Patch": "PATCH",
                        "Delete": "DELETE",
                    }
                    method = method_map.get(method, method.upper())

                    try:
                        http_method = HTTPMethod(method)
                    except ValueError:
                        continue

                    params = extract_params_from_path(path)
                    response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])
                    line_num = extract_line_number_from_pattern(content, path)

                    endpoints.append(
                        Endpoint(
                            path=path,
                            method=http_method,
                            params=params,
                            response_codes=response_codes,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="aspnet",
                        )
                    )

        return endpoints

    def _extract_python_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract Python endpoints (FastAPI, Flask, Django)."""
        endpoints = []

        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            for pattern_name, pattern in ENDPOINT_PATTERNS.items():
                if not pattern_name.startswith("py_"):
                    continue

                matches = pattern.findall(content)
                for match in matches:
                    if pattern_name == "py_flask":
                        path, method = match
                    else:
                        method, path = match

                    method = method.upper()

                    try:
                        http_method = HTTPMethod(method)
                    except ValueError:
                        continue

                    params = extract_params_from_path(path)
                    response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])
                    line_num = extract_line_number_from_pattern(content, path)

                    endpoints.append(
                        Endpoint(
                            path=path,
                            method=http_method,
                            params=params,
                            response_codes=response_codes,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework=pattern_name.replace("py_", ""),
                        )
                    )

        return endpoints

    def _extract_java_endpoints(self, project_path: Path) -> list[Endpoint]:
        """Extract Java endpoints (Spring Boot)."""
        endpoints = []

        for file_path in walk_files(project_path, ["*.java"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            for pattern_name, pattern in ENDPOINT_PATTERNS.items():
                if not pattern_name.startswith("java_"):
                    continue

                matches = pattern.findall(content)
                for match in matches:
                    method, path = match

                    method_map = {
                        "GetMapping": "GET",
                        "PostMapping": "POST",
                        "PutMapping": "PUT",
                        "PatchMapping": "PATCH",
                        "DeleteMapping": "DELETE",
                    }
                    method = method_map.get(method, "GET")

                    try:
                        http_method = HTTPMethod(method)
                    except ValueError:
                        continue

                    params = extract_params_from_path(path)
                    response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])
                    line_num = extract_line_number_from_pattern(content, path)

                    endpoints.append(
                        Endpoint(
                            path=path,
                            method=http_method,
                            params=params,
                            response_codes=response_codes,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="spring",
                        )
                    )

        return endpoints

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse API test files.

        Delegates to existing parse_test_files.py logic.
        Note: Test parsing integration tracked in #1
        """
        # For now, return empty (will be integrated with test parser)
        return []

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate API test scenarios.

        Delegates to existing calculate_input_combinations.py logic.
        Note: Scenario generation integration tracked in #2
        """
        scenarios = []

        for entry_point in entry_points:
            # Extract HTTP method and path from metadata
            method_str = entry_point.metadata.get("method", "GET")
            path = entry_point.metadata.get("path", entry_point.name)

            try:
                method = HTTPMethod(method_str)
            except ValueError:
                continue

            # Happy path scenario
            scenarios.append(
                Scenario(
                    endpoint=path,
                    method=method,
                    input_combination={"type": "valid"},
                    expected_output=200,
                    scenario_type="happy_path",
                    description=f"Valid {method_str} request to {path}",
                )
            )

            # Error scenario (e.g., missing required params)
            scenarios.append(
                Scenario(
                    endpoint=path,
                    method=method,
                    input_combination={"type": "missing_params"},
                    expected_output=400,
                    scenario_type="error",
                    description=f"Missing required parameters for {path}",
                )
            )

            # Security scenario (e.g., unauthorized)
            scenarios.append(
                Scenario(
                    endpoint=path,
                    method=method,
                    input_combination={"type": "unauthorized"},
                    expected_output=401,
                    scenario_type="security",
                    description=f"Unauthorized access to {path}",
                )
            )

        return scenarios
