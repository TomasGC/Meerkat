#!/usr/bin/env python3
"""Tests for prioritize_by_risk.py"""

import json
import sys

import pytest

from bba.models import CoverageGap, HTTPMethod, Scenario, TestFramework
from prioritize_by_risk import (
    assess_business_impact,
    assess_failure_probability,
    assess_technical_risk,
    calculate_risk_score,
    calculate_risk_stats,
    load_coverage_matrix,
)
from prioritize_by_risk import main as prioritize_main
from prioritize_by_risk import prioritize_gaps


def test_assess_business_impact_payment():
    """Test business impact for payment endpoint."""
    scenario = Scenario(
        endpoint="/payment/checkout",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=201,
        scenario_type="happy_path",
    )

    impact, reasoning = assess_business_impact(scenario)

    assert impact == 5
    assert "payment" in reasoning.lower() or "revenue" in reasoning.lower()


def test_assess_business_impact_auth():
    """Test business impact for authentication endpoint."""
    scenario = Scenario(
        endpoint="/auth/login",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )

    impact, reasoning = assess_business_impact(scenario)

    assert impact == 5
    assert "auth" in reasoning.lower() or "security" in reasoning.lower()


def test_assess_business_impact_user_write():
    """Test business impact for user write operation."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=201,
        scenario_type="happy_path",
    )

    impact, reasoning = assess_business_impact(scenario)

    assert impact >= 3  # User-facing write operation


def test_assess_business_impact_analytics():
    """Test business impact for analytics endpoint."""
    scenario = Scenario(
        endpoint="/analytics/report",
        method=HTTPMethod.GET,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )

    impact, reasoning = assess_business_impact(scenario)

    assert impact == 2  # Internal reporting


def test_assess_technical_risk_security():
    """Test technical risk for security scenario."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={"name": "<script>alert('xss')</script>"},
        expected_output=400,
        scenario_type="security",
        description="XSS test",
    )

    risk, reasoning = assess_technical_risk(scenario)

    assert risk == 5
    assert "security" in reasoning.lower()


def test_assess_technical_risk_null_handling():
    """Test technical risk for null handling."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.GET,
        input_combination={"id": None},
        expected_output=400,
        scenario_type="edge_case",
        description="Edge case: id=None",
    )

    risk, reasoning = assess_technical_risk(scenario)

    assert risk == 4
    assert "null" in reasoning.lower()


def test_assess_technical_risk_delete():
    """Test technical risk for delete operation."""
    scenario = Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.DELETE,
        input_combination={"id": "123"},
        expected_output=204,
        scenario_type="happy_path",
    )

    risk, reasoning = assess_technical_risk(scenario)

    assert risk == 4  # Delete has high technical risk


def test_assess_failure_probability_security():
    """Test failure probability for security scenario."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=400,
        scenario_type="security",
        description="SQL injection test",
    )

    probability, reasoning = assess_failure_probability(scenario)

    assert probability == 5
    assert "security" in reasoning.lower()


def test_assess_failure_probability_missing_param():
    """Test failure probability for missing required param."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.POST,
        input_combination={},
        expected_output=400,
        scenario_type="error",
        description="Missing required parameter: email",
    )

    probability, reasoning = assess_failure_probability(scenario)

    assert probability == 4
    assert "missing" in reasoning.lower()


def test_assess_failure_probability_happy_path():
    """Test failure probability for happy path."""
    scenario = Scenario(
        endpoint="/users",
        method=HTTPMethod.GET,
        input_combination={},
        expected_output=200,
        scenario_type="happy_path",
    )

    probability, reasoning = assess_failure_probability(scenario)

    assert probability == 2  # Happy path typically well-tested


def test_calculate_risk_score_critical():
    """Test critical risk level calculation."""
    risk_score, risk_level = calculate_risk_score(business_impact=5, technical_risk=5, failure_probability=5)

    assert risk_score == 125  # 5 × 5 × 5
    assert risk_level == "CRITICAL"


def test_calculate_risk_score_high():
    """Test high risk level calculation."""
    risk_score, risk_level = calculate_risk_score(business_impact=4, technical_risk=4, failure_probability=3)

    assert risk_score == 48  # 4 × 4 × 3
    assert risk_level == "HIGH"


def test_calculate_risk_score_medium():
    """Test medium risk level calculation."""
    risk_score, risk_level = calculate_risk_score(business_impact=3, technical_risk=3, failure_probability=2)

    assert risk_score == 18  # 3 × 3 × 2
    assert risk_level == "LOW"  # Just below MEDIUM threshold (20)


def test_calculate_risk_score_low():
    """Test low risk level calculation."""
    risk_score, risk_level = calculate_risk_score(business_impact=2, technical_risk=2, failure_probability=2)

    assert risk_score == 8  # 2 × 2 × 2
    assert risk_level == "LOW"


def test_prioritize_gaps():
    """Test gap prioritization."""
    # Create gaps with different risk profiles
    gaps = [
        CoverageGap(
            scenario=Scenario(
                endpoint="/payment/checkout",
                method=HTTPMethod.POST,
                input_combination={},
                expected_output=400,
                scenario_type="security",
                description="XSS test",
            ),
            is_tested=False,  # Untested
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/analytics/report",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
            ),
            is_tested=False,  # Untested
        ),
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
            ),
            is_tested=True,  # Already tested - should be skipped
        ),
    ]

    assessments = prioritize_gaps(gaps)

    # Should only include untested gaps
    assert len(assessments) == 2

    # Should be sorted by risk score (descending)
    assert assessments[0].risk_score >= assessments[1].risk_score

    # Payment security should be higher risk than analytics happy path
    payment_assessment = next(a for a in assessments if "payment" in a.gap.scenario.endpoint)
    analytics_assessment = next(a for a in assessments if "analytics" in a.gap.scenario.endpoint)

    assert payment_assessment.risk_score > analytics_assessment.risk_score


def test_calculate_risk_stats():
    """Test risk statistics calculation."""
    from bba.models import RiskAssessment

    # Create mock assessments
    assessments = [
        RiskAssessment(
            gap=CoverageGap(
                scenario=Scenario(
                    endpoint="/test",
                    method=HTTPMethod.GET,
                    input_combination={},
                    expected_output=200,
                    scenario_type="happy_path",
                ),
                is_tested=False,
            ),
            business_impact=5,
            technical_risk=5,
            failure_probability=5,
            risk_score=125,
            risk_level="CRITICAL",
            reasoning="Test",
        ),
        RiskAssessment(
            gap=CoverageGap(
                scenario=Scenario(
                    endpoint="/test",
                    method=HTTPMethod.GET,
                    input_combination={},
                    expected_output=200,
                    scenario_type="happy_path",
                ),
                is_tested=False,
            ),
            business_impact=3,
            technical_risk=3,
            failure_probability=3,
            risk_score=27,
            risk_level="MEDIUM",
            reasoning="Test",
        ),
        RiskAssessment(
            gap=CoverageGap(
                scenario=Scenario(
                    endpoint="/test",
                    method=HTTPMethod.GET,
                    input_combination={},
                    expected_output=200,
                    scenario_type="happy_path",
                ),
                is_tested=False,
            ),
            business_impact=2,
            technical_risk=2,
            failure_probability=2,
            risk_score=8,
            risk_level="LOW",
            reasoning="Test",
        ),
    ]

    stats = calculate_risk_stats(assessments)

    assert stats["total_gaps"] == 3
    assert stats["by_level"]["CRITICAL"] == 1
    assert stats["by_level"]["MEDIUM"] == 1
    assert stats["by_level"]["LOW"] == 1
    assert stats["averages"]["risk_score"] > 0


def test_prioritize_gaps_skips_tested():
    """Test that prioritization skips already tested scenarios."""
    gaps = [
        CoverageGap(
            scenario=Scenario(
                endpoint="/users",
                method=HTTPMethod.GET,
                input_combination={},
                expected_output=200,
                scenario_type="happy_path",
            ),
            is_tested=True,  # Already tested
        ),
    ]

    assessments = prioritize_gaps(gaps)

    # Should be empty because all gaps are tested
    assert len(assessments) == 0


# ── scoring tables, every branch ─────────────────────────────────────────────


def _scenario(endpoint, method=HTTPMethod.GET, scenario_type="happy_path", description="", inputs=None):
    return Scenario(
        endpoint=endpoint,
        method=method,
        input_combination=inputs or {},
        expected_output=200,
        scenario_type=scenario_type,
        description=description,
    )


@pytest.mark.parametrize(
    ("endpoint", "method", "expected"),
    [
        ("processPayment", "EXECUTE", 5),
        ("saveRecord", "EXECUTE", 4),
        ("parseHeader", "EXECUTE", 3),
        ("helper", "EXECUTE", 2),
        ("/admin/settings", HTTPMethod.GET, 4),
        ("/users/:id", HTTPMethod.GET, 3),
        ("/users/:id", HTTPMethod.DELETE, 4),
        ("/reports/daily", HTTPMethod.GET, 2),
        ("/items", HTTPMethod.POST, 3),
        ("/items", HTTPMethod.GET, 2),
    ],
)
def test_assess_business_impact_scores_by_endpoint_and_method(endpoint, method, expected):
    impact, reasoning = assess_business_impact(_scenario(endpoint, method))
    assert impact == expected
    assert reasoning


@pytest.mark.parametrize(
    ("endpoint", "method", "scenario_type", "description", "inputs", "expected"),
    [
        ("parse", "EXECUTE", "security", "", {}, 5),
        ("parse", "EXECUTE", "error", "", {"condition": "value is null"}, 4),
        ("parse", "EXECUTE", "error", "", {"condition": "len > 3"}, 3),
        ("parse", "EXECUTE", "edge_case", "", {}, 3),
        ("parse", "EXECUTE", "happy_path", "", {}, 2),
        ("/items", HTTPMethod.POST, "error", "Missing required parameter: name", {}, 4),
        ("/items", HTTPMethod.POST, "error", "Invalid email format", {}, 3),
        ("/items", HTTPMethod.POST, "error", "Server failure", {}, 3),
        ("/items", HTTPMethod.GET, "edge_case", "", {"id": None}, 4),
        ("/items", HTTPMethod.GET, "edge_case", "max length", {"id": "x"}, 3),
        ("/items", HTTPMethod.GET, "edge_case", "unicode", {"id": "x"}, 2),
        ("/items", HTTPMethod.POST, "happy_path", "", {}, 3),
        ("/items", HTTPMethod.DELETE, "happy_path", "", {}, 4),
        ("/items", HTTPMethod.GET, "happy_path", "", {}, 2),
        ("/items", HTTPMethod.GET, "load", "", {}, 2),
    ],
)
def test_assess_technical_risk_scores_each_scenario_kind(
    endpoint, method, scenario_type, description, inputs, expected
):
    risk, reasoning = assess_technical_risk(_scenario(endpoint, method, scenario_type, description, inputs))
    assert risk == expected
    assert reasoning


@pytest.mark.parametrize(
    ("endpoint", "scenario_type", "description", "inputs", "expected"),
    [
        ("parse", "error", "", {"condition": "ptr is nil"}, 4),
        ("parse", "error", "", {"condition": "x > 1"}, 3),
        ("parse", "edge_case", "", {}, 3),
        ("parse", "happy_path", "", {}, 2),
        ("/items", "security", "", {}, 5),
        ("/items", "error", "Missing param", {}, 4),
        ("/items", "error", "bad type", {}, 3),
        ("/items", "edge_case", "", {"id": None}, 4),
        ("/items", "edge_case", "empty string", {"id": ""}, 3),
        ("/items", "edge_case", "unicode", {"id": "x"}, 2),
        ("/items", "happy_path", "", {}, 2),
        ("/items", "load", "", {}, 3),
    ],
)
def test_assess_failure_probability_scores_each_scenario_kind(endpoint, scenario_type, description, inputs, expected):
    method = HTTPMethod.GET if endpoint.startswith("/") else "EXECUTE"
    probability, reasoning = assess_failure_probability(_scenario(endpoint, method, scenario_type, description, inputs))
    assert probability == expected
    assert reasoning


@pytest.mark.parametrize(
    ("scores", "level"),
    [((5, 4, 3), "CRITICAL"), ((4, 5, 2), "HIGH"), ((3, 3, 3), "MEDIUM"), ((2, 2, 2), "LOW")],
)
def test_calculate_risk_score_maps_product_to_level(scores, level):
    score, risk_level = calculate_risk_score(*scores)
    assert score == scores[0] * scores[1] * scores[2]
    assert risk_level == level


def test_calculate_risk_stats_empty_has_zero_averages():
    stats = calculate_risk_stats([])
    assert stats["total_gaps"] == 0
    assert stats["averages"] == {
        "business_impact": 0,
        "technical_risk": 0,
        "failure_probability": 0,
        "risk_score": 0,
    }


# ── load_coverage_matrix ─────────────────────────────────────────────────────


def test_load_coverage_matrix_rebuilds_gaps_and_related_tests(sample_matrix_json):
    gaps = load_coverage_matrix(sample_matrix_json)
    assert len(gaps) == 2
    tested, untested = gaps
    assert tested.is_tested is True
    assert tested.scenario.method == HTTPMethod.GET
    assert tested.related_tests[0].name == "TestGetUser"
    assert tested.related_tests[0].framework == TestFramework.GO_TESTING
    assert tested.related_tests[0].tested_method == HTTPMethod.GET
    assert untested.is_tested is False
    assert untested.related_tests == []


def test_load_coverage_matrix_keeps_non_http_action_label(temp_dir):
    matrix = {
        "gaps": [
            {
                "scenario": {
                    "endpoint": "deploy",
                    "method": "CLI",
                    "input_combination": {},
                    "expected_output": 0,
                    "scenario_type": "happy_path",
                },
                "is_tested": False,
                "related_tests": [
                    {
                        "name": "test_deploy",
                        "file_path": "tests/test_cli.py",
                        "line_number": 3,
                        "framework": "pytest",
                    }
                ],
            }
        ]
    }
    path = temp_dir / "matrix.json"
    path.write_text(json.dumps(matrix))
    [gap] = load_coverage_matrix(path)
    assert gap.scenario.method == "CLI"
    assert gap.scenario.description == ""
    assert gap.related_tests[0].tested_method is None
    assert gap.related_tests[0].test_type == "unknown"


# ── main (CLI) ───────────────────────────────────────────────────────────────


def _matrix_with_levels(temp_dir):
    """One CRITICAL gap (payment security) and one LOW gap (report read)."""
    gaps = []
    for endpoint, method, scenario_type in (
        ("/payment/charge", "POST", "security"),
        ("/reports/daily", "GET", "happy_path"),
    ):
        gaps.append(
            {
                "scenario": {
                    "endpoint": endpoint,
                    "method": method,
                    "input_combination": {},
                    "expected_output": 200,
                    "scenario_type": scenario_type,
                    "description": f"{scenario_type} on {endpoint}",
                },
                "is_tested": False,
                "related_tests": [],
            }
        )
    path = temp_dir / "matrix.json"
    path.write_text(json.dumps({"gaps": gaps}))
    return path


def test_main_writes_sorted_assessments_to_output(temp_dir, monkeypatch):
    matrix = _matrix_with_levels(temp_dir)
    out = temp_dir / "risks.json"
    monkeypatch.setattr(sys, "argv", ["prioritize_by_risk.py", str(matrix), "--output", str(out)])
    assert prioritize_main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["risk_stats"]["total_gaps"] == 2
    levels = [a["risk_level"] for a in data["risk_assessments"]]
    assert levels == ["CRITICAL", "LOW"]


def test_main_min_level_filters_lower_risks(temp_dir, monkeypatch, capsys):
    matrix = _matrix_with_levels(temp_dir)
    monkeypatch.setattr(sys, "argv", ["prioritize_by_risk.py", str(matrix), "--min-level", "HIGH"])
    assert prioritize_main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["risk_stats"]["total_gaps"] == 1
    assert data["risk_assessments"][0]["risk_level"] == "CRITICAL"


def test_main_summary_prints_levels_and_top_gaps(temp_dir, monkeypatch, capsys):
    matrix = _matrix_with_levels(temp_dir)
    monkeypatch.setattr(sys, "argv", ["prioritize_by_risk.py", str(matrix), "--summary"])
    assert prioritize_main() == 0
    err = capsys.readouterr().err
    assert "Total Missing Tests: 2" in err
    assert "CRITICAL: 1" in err
    assert "1. [CRITICAL] POST /payment/charge" in err
    assert "Risk Score:" in err


def test_main_missing_matrix_returns_one(temp_dir, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prioritize_by_risk.py", str(temp_dir / "absent.json")])
    assert prioritize_main() == 1
    assert "Error:" in capsys.readouterr().err
