#!/usr/bin/env python3
"""Tests for calculate_input_combinations.py"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from calculate_input_combinations import (
    calculate_combinations,
    generate_edge_cases_for_type,
    generate_happy_path_value,
    generate_scenarios_for_endpoint,
)
from common.models import Endpoint, HTTPMethod, Parameter


def test_generate_edge_cases_for_string():
    """Test edge case generation for string type."""
    edge_cases = generate_edge_cases_for_type("string")

    assert "" in edge_cases  # Empty string
    assert None in edge_cases  # Null
    assert any("script" in str(v).lower() for v in edge_cases)  # XSS
    assert any("drop" in str(v).lower() for v in edge_cases)  # SQL injection


def test_generate_edge_cases_for_integer():
    """Test edge case generation for integer type."""
    edge_cases = generate_edge_cases_for_type("integer")

    assert 0 in edge_cases
    assert -1 in edge_cases
    assert None in edge_cases
    assert 2147483647 in edge_cases  # MAX_INT


def test_generate_edge_cases_for_boolean():
    """Test edge case generation for boolean type."""
    edge_cases = generate_edge_cases_for_type("boolean")

    assert True in edge_cases
    assert False in edge_cases
    assert None in edge_cases


def test_generate_happy_path_value_string():
    """Test happy path value generation for string."""
    param = Parameter(name="test", param_type="body", data_type="string", required=True)
    value = generate_happy_path_value(param)

    assert isinstance(value, str)
    assert value == "test"


def test_generate_happy_path_value_integer():
    """Test happy path value generation for integer."""
    param = Parameter(name="count", param_type="query", data_type="integer", required=True)
    value = generate_happy_path_value(param)

    assert isinstance(value, int)
    assert value == 1


def test_generate_scenarios_for_endpoint_happy_path():
    """Test happy path scenario generation."""
    endpoint = Endpoint(
        path="/users/:id",
        method=HTTPMethod.GET,
        params=[Parameter(name="id", param_type="path", data_type="string", required=True)],
        response_codes=[200, 404],
        file_path="handlers.go",
        line_number=10,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have at least one happy path
    happy_paths = [s for s in scenarios if s.scenario_type == "happy_path"]
    assert len(happy_paths) >= 1
    assert happy_paths[0].expected_output == 200


def test_generate_scenarios_for_endpoint_edge_cases():
    """Test edge case scenario generation."""
    endpoint = Endpoint(
        path="/users/:id",
        method=HTTPMethod.GET,
        params=[Parameter(name="id", param_type="path", data_type="string", required=True)],
        response_codes=[200, 404],
        file_path="handlers.go",
        line_number=10,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have edge cases for the parameter
    edge_cases = [s for s in scenarios if s.scenario_type == "edge_case"]
    assert len(edge_cases) > 0


def test_generate_scenarios_for_endpoint_security():
    """Test security scenario generation."""
    endpoint = Endpoint(
        path="/users/:id",
        method=HTTPMethod.GET,
        params=[Parameter(name="id", param_type="path", data_type="string", required=True)],
        response_codes=[200, 404],
        file_path="handlers.go",
        line_number=10,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have security tests (XSS, SQL injection, etc.)
    security_tests = [s for s in scenarios if s.scenario_type == "security"]
    assert len(security_tests) >= 4  # XSS, SQL, path traversal, command injection


def test_generate_scenarios_for_endpoint_missing_required():
    """Test missing required parameter scenarios."""
    endpoint = Endpoint(
        path="/users",
        method=HTTPMethod.POST,
        params=[
            Parameter(name="email", param_type="body", data_type="string", required=True),
            Parameter(name="name", param_type="body", data_type="string", required=True),
        ],
        response_codes=[201, 400],
        file_path="handlers.go",
        line_number=20,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have error scenarios for missing required params
    error_scenarios = [
        s
        for s in scenarios
        if s.scenario_type == "error" and "missing" in s.description.lower()
    ]
    assert len(error_scenarios) == 2  # One for each required param


def test_generate_scenarios_for_endpoint_post_empty_body():
    """Test POST with empty body scenario."""
    endpoint = Endpoint(
        path="/users",
        method=HTTPMethod.POST,
        params=[
            Parameter(name="email", param_type="body", data_type="string", required=True),
        ],
        response_codes=[201, 400],
        file_path="handlers.go",
        line_number=20,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have POST with empty body error scenario
    empty_body_scenarios = [
        s
        for s in scenarios
        if s.scenario_type == "error" and "empty body" in s.description.lower()
    ]
    assert len(empty_body_scenarios) == 1


def test_generate_scenarios_for_endpoint_delete_nonexistent():
    """Test DELETE non-existent resource scenario."""
    endpoint = Endpoint(
        path="/users/:id",
        method=HTTPMethod.DELETE,
        params=[Parameter(name="id", param_type="path", data_type="string", required=True)],
        response_codes=[204, 404],
        file_path="handlers.go",
        line_number=30,
    )

    scenarios = generate_scenarios_for_endpoint(endpoint)

    # Should have DELETE non-existent scenario
    nonexistent_scenarios = [
        s
        for s in scenarios
        if s.scenario_type == "error" and "non-existent" in s.description.lower()
    ]
    assert len(nonexistent_scenarios) == 1
    assert nonexistent_scenarios[0].expected_output == 404


def test_calculate_combinations(sample_endpoints_json):
    """Test full combination calculation from endpoints file."""
    scenarios = calculate_combinations(sample_endpoints_json)

    # Should have scenarios for all endpoints
    assert len(scenarios) > 0

    # Should have all scenario types
    types = {s.scenario_type for s in scenarios}
    assert "happy_path" in types
    assert "edge_case" in types
    assert "error" in types
    assert "security" in types

    # Check endpoints are covered
    endpoints = {s.endpoint for s in scenarios}
    assert "/users/:id" in endpoints
    assert "/users" in endpoints


def test_calculate_combinations_breakdown(sample_endpoints_json):
    """Test scenario breakdown counts."""
    scenarios = calculate_combinations(sample_endpoints_json)

    happy_path_count = len([s for s in scenarios if s.scenario_type == "happy_path"])
    edge_case_count = len([s for s in scenarios if s.scenario_type == "edge_case"])
    error_count = len([s for s in scenarios if s.scenario_type == "error"])
    security_count = len([s for s in scenarios if s.scenario_type == "security"])

    # All should be > 0
    assert happy_path_count > 0
    assert edge_case_count > 0
    assert error_count > 0
    assert security_count > 0
