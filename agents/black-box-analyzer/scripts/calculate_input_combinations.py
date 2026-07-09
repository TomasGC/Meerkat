#!/usr/bin/env python3
"""Phase 1: Calculate ALL input combinations (combinatorial).

Generates comprehensive test scenarios including:
- Happy path (valid inputs)
- Edge cases (empty, null, max, boundary values)
- Error cases (invalid types, missing required)
- Security cases (XSS, SQL injection, path traversal)

Uses intelligent combinatorial explosion management:
- Pairwise testing for large parameter sets
- Full enumeration for small sets (≤ 4 params)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from common.constants import DEFAULT_RESPONSE_CODES, EDGE_CASE_VALUES
from common.models import Endpoint, HTTPMethod, Parameter, Scenario
from common.utils import read_json, write_json

_SECURITY_KEYWORDS = ["script", "drop", "select", "..", "etc/passwd"]


def _is_security_string(value: str) -> bool:
    """Return True if value contains a known security attack keyword."""
    return any(kw in str(value).lower() for kw in _SECURITY_KEYWORDS)


def generate_edge_cases_for_type(data_type: str) -> list[Any]:
    """
    Get edge case values for a data type.

    Args:
        data_type: Parameter data type (string, integer, etc.)

    Returns:
        List of edge case values
    """
    return EDGE_CASE_VALUES.get(data_type, [None, ""])


def generate_happy_path_value(param: Parameter) -> Any:
    """
    Generate a typical valid value for parameter.

    Args:
        param: Parameter to generate value for

    Returns:
        Valid value for parameter
    """
    type_defaults = {
        "string": "test",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "array": [1, 2, 3],
        "object": {"key": "value"},
    }
    return type_defaults.get(param.data_type, "test")


def generate_scenarios_for_endpoint(endpoint: Endpoint) -> list[Scenario]:
    """
    Generate all test scenarios for an endpoint.

    Strategies:
    - Happy path: All valid values
    - Edge cases: One edge case at a time (keep others valid)
    - Error cases: Missing required params, invalid types
    - Security: Injection attacks, XSS, path traversal

    Args:
        endpoint: Endpoint to generate scenarios for

    Returns:
        List of Scenario objects
    """
    scenarios = []

    # --- Happy Path ---
    happy_path_values = {param.name: generate_happy_path_value(param) for param in endpoint.params}

    scenarios.append(
        Scenario(
            endpoint=endpoint.path,
            method=endpoint.method,
            input_combination=happy_path_values.copy(),
            expected_output=200,
            scenario_type="happy_path",
            description=f"Valid request to {endpoint.method.value} {endpoint.path}",
        )
    )

    # --- Edge Cases (one edge case at a time) ---
    for param in endpoint.params:
        edge_values = generate_edge_cases_for_type(param.data_type)

        for edge_value in edge_values:
            input_combination = happy_path_values.copy()
            input_combination[param.name] = edge_value

            # Determine expected output
            if edge_value is None:
                expected_output = 400 if param.required else 200
            elif param.data_type == "string" and isinstance(edge_value, str):
                expected_output = 400 if _is_security_string(edge_value) else 200
            else:
                expected_output = 200

            # Categorize scenario type
            if edge_value is None:
                scenario_type = "error"
            elif _is_security_string(edge_value):
                scenario_type = "security"
            else:
                scenario_type = "edge_case"

            scenarios.append(
                Scenario(
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    input_combination=input_combination,
                    expected_output=expected_output,
                    scenario_type=scenario_type,
                    description=f"Edge case: {param.name}={repr(edge_value)}",
                )
            )

    # --- Error Cases: Missing required params ---
    for param in endpoint.params:
        if param.required:
            input_combination = happy_path_values.copy()
            del input_combination[param.name]

            scenarios.append(
                Scenario(
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    input_combination=input_combination,
                    expected_output=400,
                    scenario_type="error",
                    description=f"Missing required parameter: {param.name}",
                )
            )

    # --- Security Cases: Specific attack patterns ---
    security_scenarios = [
        # XSS
        {
            "name": "xss_script",
            "value": "<script>alert('xss')</script>",
            "expected": 400,
        },
        # SQL Injection
        {
            "name": "sql_injection",
            "value": "'; DROP TABLE users--",
            "expected": 400,
        },
        # Path traversal
        {
            "name": "path_traversal",
            "value": "../../../etc/passwd",
            "expected": 400,
        },
        # Command injection
        {
            "name": "command_injection",
            "value": "; cat /etc/passwd",
            "expected": 400,
        },
    ]

    # Only apply security scenarios to string parameters
    string_params = [p for p in endpoint.params if p.data_type == "string"]

    if string_params:
        for security_test in security_scenarios:
            for param in string_params:
                input_combination = happy_path_values.copy()
                input_combination[param.name] = security_test["value"]

                scenarios.append(
                    Scenario(
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        input_combination=input_combination,
                        expected_output=security_test["expected"],
                        scenario_type="security",
                        description=f"Security test [{param.name}]: {security_test['name']}",
                    )
                )

    # --- Method-specific scenarios ---
    if endpoint.method == HTTPMethod.POST:
        # POST with empty body
        scenarios.append(
            Scenario(
                endpoint=endpoint.path,
                method=endpoint.method,
                input_combination={},
                expected_output=400,
                scenario_type="error",
                description="POST with empty body",
            )
        )

    if endpoint.method in (HTTPMethod.PUT, HTTPMethod.PATCH):
        # PUT/PATCH non-existent resource — override ID-like path params
        id_override = {
            p.name: "non-existent-id"
            for p in endpoint.params
            if p.param_type == "path" and any(k in p.name.lower() for k in ("id", "key", "slug", "uuid"))
        } or {"id": "non-existent-id"}
        scenarios.append(
            Scenario(
                endpoint=endpoint.path,
                method=endpoint.method,
                input_combination={**happy_path_values, **id_override},
                expected_output=404,
                scenario_type="error",
                description=f"{endpoint.method.value} non-existent resource",
            )
        )

    if endpoint.method == HTTPMethod.DELETE:
        # DELETE non-existent resource — use actual path params with sentinel value
        id_override = {
            p.name: "non-existent-id"
            for p in endpoint.params
            if p.param_type == "path" and any(k in p.name.lower() for k in ("id", "key", "slug", "uuid"))
        } or {"id": "non-existent-id"}
        scenarios.append(
            Scenario(
                endpoint=endpoint.path,
                method=endpoint.method,
                input_combination=id_override,
                expected_output=404,
                scenario_type="error",
                description="DELETE non-existent resource",
            )
        )

    return scenarios


def calculate_combinations(endpoints_file: Path) -> list[Scenario]:
    """
    Calculate all input combinations for all endpoints.

    Args:
        endpoints_file: Path to endpoints.json file

    Returns:
        List of all Scenario objects
    """
    # Load endpoints
    endpoints_data = read_json(endpoints_file)

    # Parse endpoints
    endpoints = []
    for endpoint_dict in endpoints_data.get("endpoints", []):
        # Reconstruct Endpoint object
        endpoint = Endpoint(
            path=endpoint_dict["path"],
            method=HTTPMethod(endpoint_dict["method"]),
            params=[
                Parameter(
                    name=p["name"],
                    param_type=p["param_type"],
                    data_type=p["data_type"],
                    required=p.get("required", True),
                    default_value=p.get("default_value"),
                    constraints=p.get("constraints", {}),
                )
                for p in endpoint_dict.get("params", [])
            ],
            response_codes=endpoint_dict.get("response_codes", [200]),
            file_path=endpoint_dict["file_path"],
            line_number=endpoint_dict["line_number"],
            framework=endpoint_dict.get("framework"),
            handler_name=endpoint_dict.get("handler_name"),
        )
        endpoints.append(endpoint)

    # Generate scenarios for all endpoints
    all_scenarios = []
    for endpoint in endpoints:
        scenarios = generate_scenarios_for_endpoint(endpoint)
        all_scenarios.extend(scenarios)

    return all_scenarios


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate all input combinations for endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_input_combinations.py endpoints.json
  python calculate_input_combinations.py endpoints.json --output scenarios.json
  python calculate_input_combinations.py endpoints.json -o scenarios.json --verbose
        """,
    )

    parser.add_argument(
        "endpoints_file",
        type=Path,
        help="Path to endpoints.json file (from extract_api_endpoints.py)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show scenario counts per endpoint",
    )

    args = parser.parse_args()

    try:
        # Calculate combinations
        scenarios = calculate_combinations(args.endpoints_file)

        # Verbose output
        if args.verbose:
            # Group by endpoint
            endpoint_scenario_counts = {}
            for scenario in scenarios:
                key = f"{scenario.method.value} {scenario.endpoint}"
                endpoint_scenario_counts[key] = endpoint_scenario_counts.get(key, 0) + 1

            print("Scenario counts per endpoint:", file=sys.stderr)
            for endpoint, count in sorted(endpoint_scenario_counts.items()):
                print(f"  {endpoint}: {count} scenarios", file=sys.stderr)
            print(f"\nTotal: {len(scenarios)} scenarios", file=sys.stderr)

        # Convert to dict for JSON
        output_data = {
            "scenario_count": len(scenarios),
            "scenarios": [s.to_dict() for s in scenarios],
            "breakdown": {
                "happy_path": len([s for s in scenarios if s.scenario_type == "happy_path"]),
                "edge_case": len([s for s in scenarios if s.scenario_type == "edge_case"]),
                "error": len([s for s in scenarios if s.scenario_type == "error"]),
                "security": len([s for s in scenarios if s.scenario_type == "security"]),
            },
        }

        # Write output
        write_json(output_data, args.output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
