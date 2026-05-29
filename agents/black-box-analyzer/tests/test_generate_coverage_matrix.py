#!/usr/bin/env python3
"""Tests for generate_coverage_matrix.py"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from common.models import HTTPMethod, Scenario, TestCase, TestFramework
from generate_coverage_matrix import (
    calculate_coverage_stats,
    find_related_tests,
    generate_coverage_matrix,
    generate_markdown_table,
    scenario_matches_test,
)


def test_scenario_matches_test_exact_match():
    """Test exact endpoint and method match."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.GET,
        input_combination={"id": "123"},
        expected_output=200,
        scenario_type="happy_path",
        description="Get user by ID",
    )

    test = TestCase(
        name="TestGetUser",
        file_path="users_test.go",
        line_number=10,
        framework=TestFramework.GO_TESTING,
        tested_endpoint="/users/:id",
        tested_method=HTTPMethod.GET,
    )

    assert scenario_matches_test(scenario, test) is True


def test_scenario_matches_test_method_mismatch():
    """Test method mismatch returns False."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.GET,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )

    test = TestCase(
        name="TestDeleteUser",
        file_path="users_test.go",
        line_number=20,
        framework=TestFramework.GO_TESTING,
        tested_endpoint="/users/:id",
        tested_method=HTTPMethod.DELETE,
    )

    assert scenario_matches_test(scenario, test) is False


def test_scenario_matches_test_happy_path_keyword():
    """Test happy path keyword matching."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=201,
        scenario_type="happy_path",
    )

    test = TestCase(
        name="TestCreateUserSuccess",
        file_path="users_test.go",
        line_number=30,
        framework=TestFramework.GO_TESTING,
        tested_endpoint="/users",
        tested_method=HTTPMethod.POST,
    )

    assert scenario_matches_test(scenario, test) is True


def test_scenario_matches_test_error_keyword():
    """Test error case keyword matching."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=400,
        scenario_type="error",
        description="Missing required field",
    )

    test = TestCase(
        name="TestCreateUserInvalidInput",
        file_path="users_test.go",
        line_number=40,
        framework=TestFramework.GO_TESTING,
        tested_endpoint="/users",
        tested_method=HTTPMethod.POST,
    )

    assert scenario_matches_test(scenario, test) is True


def test_scenario_matches_test_security_keyword():
    """Test security case keyword matching."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=400,
        scenario_type="security",
        description="XSS injection test",
    )

    test = TestCase(
        name="TestCreateUserXSSProtection",
        file_path="users_test.go",
        line_number=50,
        framework=TestFramework.GO_TESTING,
        tested_endpoint="/users",
        tested_method=HTTPMethod.POST,
    )

    assert scenario_matches_test(scenario, test) is True


def test_find_related_tests():
    """Test finding related tests for a scenario."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.GET,
        input_combination={"id": "123"},
        expected_output=200,
        scenario_type="happy_path",
    )

    all_tests = [
        TestCase(
            name="TestGetUser",
            file_path="users_test.go",
            line_number=10,
            framework=TestFramework.GO_TESTING,
            tested_endpoint="/users/:id",
            tested_method=HTTPMethod.GET,
        ),
        TestCase(
            name="TestDeleteUser",
            file_path="users_test.go",
            line_number=20,
            framework=TestFramework.GO_TESTING,
            tested_endpoint="/users/:id",
            tested_method=HTTPMethod.DELETE,
        ),
    ]

    related = find_related_tests(scenario, all_tests)

    assert len(related) == 1
    assert related[0].name == "TestGetUser"


def test_calculate_coverage_stats():
    """Test coverage statistics calculation."""
    from common.models import CoverageGap

    # Mock coverage gaps
    gaps = [
        CoverageGap(
            scenario=Scenario(
                endpoint="/users/:id",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
            ),
            is_tested=True,
            related_tests=[],
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users/:id",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=400,
                scenario_type="error",
            ),
            is_tested=False,
            related_tests=[],
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.POST,
                input_combination={},
                expected_output=201,
                scenario_type="happy_path",
            ),
            is_tested=True,
            related_tests=[],
        ),
    ]

    stats = calculate_coverage_stats(gaps)

    assert stats["total_scenarios"] == 3
    assert stats["tested_scenarios"] == 2
    assert stats["untested_scenarios"] == 1
    assert stats["coverage_percent"] == 66.67


def test_calculate_coverage_stats_by_type():
    """Test coverage statistics by scenario type."""
    from common.models import CoverageGap

    gaps = [
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
            ),
            is_tested=True,
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=400,
                scenario_type="error",
            ),
            is_tested=False,
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=400,
                scenario_type="security",
            ),
            is_tested=False,
        ),
    ]

    stats = calculate_coverage_stats(gaps)

    assert stats["by_type"]["happy_path"]["coverage_percent"] == 100.0
    assert stats["by_type"]["error"]["coverage_percent"] == 0.0
    assert stats["by_type"]["security"]["coverage_percent"] == 0.0


def test_generate_markdown_table():
    """Test markdown table generation."""
    from common.models import CoverageGap

    gaps = [
        CoverageGap(
            scenario=Scenario(
                endpoint="/users/:id",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
                description="Valid GET request",
            ),
            is_tested=True,
            related_tests=[],
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users/:id",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=404,
                scenario_type="error",
                description="User not found",
            ),
            is_tested=False,
            related_tests=[],
        ),
    ]

    markdown = generate_markdown_table(gaps)

    assert "# Test Coverage Matrix" in markdown
    assert "## GET /users/:id" in markdown
    assert "✅" in markdown  # Tested scenario
    assert "❌" in markdown  # Untested scenario
    assert "Coverage" in markdown


def test_generate_coverage_matrix(sample_scenarios_json, sample_tests_json):
    """Test full coverage matrix generation."""
    coverage_gaps = generate_coverage_matrix(sample_scenarios_json, sample_tests_json)

    assert len(coverage_gaps) > 0

    # Should have tested scenarios
    tested_count = len([g for g in coverage_gaps if g.is_tested])
    untested_count = len([g for g in coverage_gaps if not g.is_tested])

    assert tested_count > 0
    # Untested count may be 0 if all scenarios are covered
