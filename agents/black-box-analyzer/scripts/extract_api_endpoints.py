#!/usr/bin/env python3
"""Phase 1: Extract ALL API endpoints with params/responses.

Intelligent multi-language endpoint extraction using AST parsing and regex.

Supports:
- Go: gin, echo, fiber, chi, mux
- TypeScript: Express, NestJS, Fastify
- C#: ASP.NET (attributes + minimal APIs)
- Python: FastAPI, Flask, Django
- Java: Spring Boot
"""

import argparse
import json
import re
import sys
from pathlib import Path

from common.constants import (
    DEFAULT_RESPONSE_CODES,
    ENDPOINT_PATTERNS,
    LANGUAGE_INDICATORS,
)
from common.models import Endpoint, HTTPMethod, Language, Parameter
from common.utils import (
    extract_line_number_from_pattern,
    extract_params_from_path,
    format_path_relative,
    read_file_safe,
    walk_files,
    write_json,
)


def detect_language(project_path: Path) -> Language:
    """Detect project language from indicator files."""
    for language, indicators in LANGUAGE_INDICATORS.items():
        for indicator in indicators:
            if "*" in indicator:
                if list(project_path.glob(indicator)):
                    return Language(language)
            else:
                if (project_path / indicator).exists():
                    return Language(language)
    return Language.UNKNOWN



def extract_go_endpoints(project_path: Path) -> list[Endpoint]:
    """Extract endpoints from Go code (gin, echo, fiber, chi, mux)."""
    endpoints = []

    for file_path in walk_files(project_path, ["*.go"]):
        content = read_file_safe(file_path)
        if not content:
            continue

        # Try each Go framework pattern
        for pattern_name, pattern in ENDPOINT_PATTERNS.items():
            if not pattern_name.startswith("go_"):
                continue

            matches = pattern.findall(content)
            for match in matches:
                # Parse match based on pattern
                if pattern_name == "go_mux":
                    # mux: (path, method)
                    path, method = match
                else:
                    # gin/echo/fiber/chi: (method, path)
                    method, path = match

                # Normalize method to uppercase
                method = method.upper()

                try:
                    http_method = HTTPMethod(method)
                except ValueError:
                    continue

                # Extract parameters
                params = extract_params_from_path(path)

                # Default response codes by method
                response_codes = DEFAULT_RESPONSE_CODES.get(method, [200, 400, 500])

                # Find line number
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


def extract_typescript_endpoints(project_path: Path) -> list[Endpoint]:
    """Extract endpoints from TypeScript code (Express, NestJS, Fastify)."""
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
                # (method, path)
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


def extract_csharp_endpoints(project_path: Path) -> list[Endpoint]:
    """Extract endpoints from C# code (ASP.NET attributes + minimal APIs)."""
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
                # (method, path)
                method, path = match

                # Handle empty path (defaults to controller route)
                if not path:
                    path = "/"

                # Normalize method
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


def extract_python_endpoints(project_path: Path) -> list[Endpoint]:
    """Extract endpoints from Python code (FastAPI, Flask, Django)."""
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
                    # Flask: (path, method)
                    path, method = match
                else:
                    # FastAPI: (method, path)
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


def extract_java_endpoints(project_path: Path) -> list[Endpoint]:
    """Extract endpoints from Java code (Spring Boot)."""
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
                # (method_annotation, path)
                method_annotation, path = match

                # Map annotation to HTTP method
                method_map = {
                    "GetMapping": "GET",
                    "PostMapping": "POST",
                    "PutMapping": "PUT",
                    "PatchMapping": "PATCH",
                    "DeleteMapping": "DELETE",
                }
                method = method_map.get(method_annotation, "GET")

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


def extract_endpoints(project_path: Path, language: Language | None = None) -> list[Endpoint]:
    """
    Extract all API endpoints from project.

    Args:
        project_path: Project root directory
        language: Language to parse (auto-detect if None)

    Returns:
        List of Endpoint objects
    """
    if not language:
        language = detect_language(project_path)

    if language == Language.GO:
        return extract_go_endpoints(project_path)
    elif language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
        return extract_typescript_endpoints(project_path)
    elif language == Language.CSHARP:
        return extract_csharp_endpoints(project_path)
    elif language == Language.PYTHON:
        return extract_python_endpoints(project_path)
    elif language == Language.JAVA:
        return extract_java_endpoints(project_path)
    else:
        return []  # Language not supported for endpoint extraction — return empty


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract API endpoints from source code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_api_endpoints.py /path/to/project
  python extract_api_endpoints.py . --language go --output endpoints.json
  python extract_api_endpoints.py ~/myapp --language typescript
        """,
    )

    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to project root directory",
    )

    parser.add_argument(
        "--language",
        "-l",
        type=str,
        choices=["go", "typescript", "javascript", "csharp", "python", "java"],
        help="Project language (auto-detect if not specified)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    args = parser.parse_args()

    try:
        # Parse language
        language = Language(args.language) if args.language else None

        # Extract endpoints
        endpoints = extract_endpoints(args.project_path, language)

        # Convert to dict for JSON
        output_data = {
            "endpoint_count": len(endpoints),
            "endpoints": [ep.to_dict() for ep in endpoints],
        }

        # Write output
        write_json(output_data, args.output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
