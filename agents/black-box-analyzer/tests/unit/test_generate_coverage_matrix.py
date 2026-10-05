#!/usr/bin/env python3
"""Tests for generate_coverage_matrix.py"""

import json

from bba.models import HTTPMethod, Scenario, TestCase, TestFramework
from generate_coverage_matrix import (
    calculate_coverage_stats,
    find_related_tests,
    generate_coverage_matrix,
    generate_markdown_table,
    scenario_matches_test,
    scenario_matches_test_library,
)

# Add scripts directory to path


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
    from bba.models import CoverageGap

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
    from bba.models import CoverageGap

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
    from bba.models import CoverageGap

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

    assert tested_count > 0


def test_scenario_matches_test_none_tested_endpoint():
    """tested_endpoint=None must not raise — scenario never matches."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.GET,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )
    test = TestCase(
        name="TestSomething",
        file_path="t.go",
        line_number=1,
        framework=TestFramework.GO_TESTING,
        tested_endpoint=None,
        tested_method=None,
    )
    result = scenario_matches_test(scenario, test)
    assert result is False


def test_calculate_coverage_stats_zero_scenarios():
    """Empty gaps list must not raise ZeroDivisionError."""
    stats = calculate_coverage_stats([])
    assert stats["total_scenarios"] == 0
    assert stats["coverage_percent"] == 0.0


def _scenario(endpoint="/users/{id}", scenario_type="happy_path", description="", condition=None):
    return Scenario(
        endpoint=endpoint,
        method=HTTPMethod.GET,
        input_combination={"condition": condition} if condition is not None else {},
        expected_output=200,
        scenario_type=scenario_type,
        description=description,
    )


def _test(name, endpoint=None, method=None):
    return TestCase(
        name=name,
        file_path="t.py",
        line_number=1,
        framework=TestFramework.PYTEST,
        tested_endpoint=endpoint,
        tested_method=method,
    )


def test_library_match_needs_method_and_condition_words():
    scenario = _scenario(endpoint="Parser.parse_header", condition="input is empty")
    assert scenario_matches_test_library(scenario, _test("test_parse_header_when_empty")) is True
    assert scenario_matches_test_library(scenario, _test("test_parse_header_valid")) is False
    assert scenario_matches_test_library(scenario, _test("test_other_thing_empty")) is False


def test_find_related_tests_library_mode_uses_keyword_matcher():
    scenario = _scenario(endpoint="cache.evict_entry", condition="ttl expired")
    tests = [_test("test_evict_entry_expired"), _test("test_evict_entry_fresh")]
    related = find_related_tests(scenario, tests, mode="library")
    assert [t.name for t in related] == ["test_evict_entry_expired"]


def test_scenario_matches_test_brace_id_equals_colon_id():
    test = _test("test_get_user_success", endpoint="/users/:id", method=HTTPMethod.GET)
    assert scenario_matches_test(_scenario(endpoint="/users/{id}"), test) is True


def test_scenario_matches_test_different_path_rejected():
    test = _test("test_get_order_success", endpoint="/orders/:id", method=HTTPMethod.GET)
    assert scenario_matches_test(_scenario(endpoint="/users/{id}"), test) is False


def test_scenario_matches_test_missing_param_error_case():
    scenario = _scenario(scenario_type="error", description="Missing required parameter: id")
    assert scenario_matches_test(scenario, _test("test_missing_id_returns_400")) is True


def test_scenario_matches_test_edge_case_keyword_without_endpoint():
    scenario = _scenario(scenario_type="edge_case")
    assert scenario_matches_test(scenario, _test("test_handles_empty_name")) is True
    assert scenario_matches_test(scenario, _test("test_handles_name")) is False


def test_generate_markdown_table_truncates_related_tests_to_three():
    from bba.models import CoverageGap

    gap = CoverageGap(
        scenario=_scenario(description="Valid"),
        is_tested=True,
        related_tests=[_test(f"t{i}") for i in range(5)],
    )
    markdown = generate_markdown_table([gap])
    assert "t0, t1, t2 (+2 more)" in markdown


# ── main ──────────────────────────────────────────────────────────────────────


def _run_main(monkeypatch, *argv):
    import generate_coverage_matrix

    monkeypatch.setattr("sys.argv", ["generate_coverage_matrix.py", *map(str, argv)])
    return generate_coverage_matrix.main()


def test_main_writes_json_markdown_and_summary(sample_scenarios_json, sample_tests_json, temp_dir, monkeypatch, capsys):
    out = temp_dir / "matrix.json"
    md = temp_dir / "matrix.md"
    rc = _run_main(monkeypatch, sample_scenarios_json, sample_tests_json, "-o", out, "--markdown", md, "--summary")
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["coverage_stats"]["total_scenarios"] == 5
    assert len(data["gaps"]) == 5
    assert md.read_text(encoding="utf-8").startswith("# Test Coverage Matrix")
    err = capsys.readouterr().err
    assert "Total Scenarios: 5" in err
    assert "By Scenario Type:" in err
    assert "Markdown table written to" in err


def test_main_library_mode_prints_json(sample_scenarios_json, sample_tests_json, monkeypatch, capsys):
    assert _run_main(monkeypatch, sample_scenarios_json, sample_tests_json, "--mode", "library") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["coverage_stats"]["total_scenarios"] == 5


def test_main_missing_input_returns_one(temp_dir, sample_tests_json, monkeypatch, capsys):
    assert _run_main(monkeypatch, temp_dir / "missing.json", sample_tests_json) == 1
    assert "Error:" in capsys.readouterr().err
