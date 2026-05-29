#!/usr/bin/env python3
"""Tests for prioritize_by_risk.py"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from common.models import CoverageGap, HTTPMethod, Scenario
from prioritize_by_risk import (
    assess_business_impact,
    assess_failure_probability,
    assess_technical_risk,
    calculate_risk_score,
    calculate_risk_stats,
    prioritize_gaps,
)


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
    risk_score, risk_level = calculate_risk_score(
        business_impact=5, technical_risk=5, failure_probability=5
    )

    assert risk_score == 125  # 5 × 5 × 5
    assert risk_level == "CRITICAL"


def test_calculate_risk_score_high():
    """Test high risk level calculation."""
    risk_score, risk_level = calculate_risk_score(
        business_impact=4, technical_risk=4, failure_probability=3
    )

    assert risk_score == 48  # 4 × 4 × 3
    assert risk_level == "HIGH"


def test_calculate_risk_score_medium():
    """Test medium risk level calculation."""
    risk_score, risk_level = calculate_risk_score(
        business_impact=3, technical_risk=3, failure_probability=2
    )

    assert risk_score == 18  # 3 × 3 × 2
    assert risk_level == "LOW"  # Just below MEDIUM threshold (20)


def test_calculate_risk_score_low():
    """Test low risk level calculation."""
    risk_score, risk_level = calculate_risk_score(
        business_impact=2, technical_risk=2, failure_probability=2
    )

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
    from common.models import RiskAssessment

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
