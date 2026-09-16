#!/usr/bin/env python3
"""Tests for common/models.py from_dict deserialization."""

import pytest

from common.models import (
    AnalysisResult,
    CoverageGap,
    CoverageMatrix,
    Endpoint,
    EntryPoint,
    EntryPointType,
    HTTPMethod,
    Parameter,
    ProjectType,
    RiskAssessment,
    Scenario,
)
# Aliased: pytest tries to collect module-level names starting with "Test"
from common.models import TestCase as TestCaseModel
from common.models import TestFramework as TestFrameworkModel

# ── builders ──────────────────────────────────────────────────────────────────

def _parameter() -> Parameter:
    return Parameter(
        name="id",
        param_type="path",
        data_type="string",
        required=True,
        default_value="none",
        constraints={"min": 1},
    )

def _test_case() -> TestCaseModel:
    return TestCaseModel(
        name="TestGetUser",
        file_path="users_test.go",
        line_number=12,
        framework=TestFrameworkModel.GO_TESTING,
        tested_endpoint="/users/:id",
        tested_method=HTTPMethod.GET,
        tested_inputs=["id"],
        expected_outputs=["200"],
        test_type="unit",
    )

def _scenario() -> Scenario:
    return Scenario(
        endpoint="/users/:id",
        method=HTTPMethod.DELETE,
        input_combination={"id": None},
        expected_output=400,
        scenario_type="error",
        description="missing id",
    )

def _gap() -> CoverageGap:
    return CoverageGap(scenario=_scenario(), is_tested=True, related_tests=[_test_case()])

def _risk() -> RiskAssessment:
    return RiskAssessment(
        gap=_gap(),
        business_impact=5,
        technical_risk=4,
        failure_probability=3,
        risk_score=60,
        risk_level="CRITICAL",
        reasoning="deletes data",
    )

def _matrix() -> CoverageMatrix:
    return CoverageMatrix(
        total_scenarios=10,
        tested_scenarios=3,
        untested_scenarios=7,
        coverage_percent=12.345,
        gaps=[_gap()],
        by_endpoint={"GET /users": {"total": 2}},
    )

def _result() -> AnalysisResult:
    return AnalysisResult(
        project_type=ProjectType.REST_API,
        entry_points=[
            EntryPoint(
                type=EntryPointType.HTTP_ENDPOINT,
                name="/users/:id",
                params=[_parameter()],
                file_path="main.go",
                line_number=7,
                framework="gin",
                metadata={"handler": "getUser"},
            )
        ],
        test_cases=[_test_case()],
        scenarios=[_scenario()],
        coverage_matrix=_matrix(),
        risk_assessment=[_risk()],
        metadata={"analyzer": "APIAnalyzer"},
    )

# ── Parameter ─────────────────────────────────────────────────────────────────

def test_parameter_roundtrip():
    restored = Parameter.from_dict(_parameter().to_dict())
    assert restored == _parameter()

def test_parameter_from_dict_applies_defaults():
    restored = Parameter.from_dict({"name": "q", "param_type": "query", "data_type": "string"})
    assert restored.required is True
    assert restored.default_value is None
    assert restored.constraints == {}

# ── EntryPoint ────────────────────────────────────────────────────────────────

def test_entry_point_roundtrip_restores_enum():
    original = _result().entry_points[0]
    restored = EntryPoint.from_dict(original.to_dict())
    assert restored == original
    assert isinstance(restored.type, EntryPointType)
    assert isinstance(restored.params[0], Parameter)

# ── Endpoint ──────────────────────────────────────────────────────────────────

def test_endpoint_roundtrip_restores_enum():
    original = Endpoint(
        path="/users",
        method=HTTPMethod.POST,
        params=[_parameter()],
        response_codes=[201, 400],
        file_path="main.go",
        line_number=3,
        framework="gin",
        handler_name="createUser",
    )
    restored = Endpoint.from_dict(original.to_dict())
    assert restored == original
    assert isinstance(restored.method, HTTPMethod)

# ── TestCase ──────────────────────────────────────────────────────────────────

def test_test_case_roundtrip_restores_enums():
    restored = TestCaseModel.from_dict(_test_case().to_dict())
    assert restored == _test_case()
    assert isinstance(restored.framework, TestFrameworkModel)
    assert isinstance(restored.tested_method, HTTPMethod)

def test_test_case_from_dict_keeps_none_method():
    payload = _test_case().to_dict()
    payload["tested_method"] = None
    assert TestCaseModel.from_dict(payload).tested_method is None

# ── Scenario / CoverageGap ────────────────────────────────────────────────────

def test_scenario_roundtrip():
    restored = Scenario.from_dict(_scenario().to_dict())
    assert restored == _scenario()
    assert isinstance(restored.method, HTTPMethod)

def test_coverage_gap_roundtrip_nests_objects():
    restored = CoverageGap.from_dict(_gap().to_dict())
    assert restored == _gap()
    assert isinstance(restored.scenario, Scenario)
    assert isinstance(restored.related_tests[0], TestCaseModel)

# ── RiskAssessment ────────────────────────────────────────────────────────────

def test_risk_assessment_roundtrip():
    restored = RiskAssessment.from_dict(_risk().to_dict())
    assert restored == _risk()
    assert isinstance(restored.gap, CoverageGap)

# ── CoverageMatrix ────────────────────────────────────────────────────────────

def test_coverage_matrix_roundtrip_rounds_percent():
    restored = CoverageMatrix.from_dict(_matrix().to_dict())
    # to_dict rounds to 2 decimals, so the round-trip is lossy by design
    assert restored.coverage_percent == pytest.approx(12.345, abs=0.01)
    assert restored.total_scenarios == 10
    assert restored.by_endpoint == {"GET /users": {"total": 2}}
    assert isinstance(restored.gaps[0], CoverageGap)

# ── AnalysisResult ────────────────────────────────────────────────────────────

def test_analysis_result_roundtrip_is_stable():
    payload = _result().to_dict()
    # Second serialization must match the first: nothing is lost on rebuild
    assert AnalysisResult.from_dict(payload).to_dict() == payload

def test_analysis_result_roundtrip_restores_types():
    restored = AnalysisResult.from_dict(_result().to_dict())
    assert isinstance(restored.project_type, ProjectType)
    assert isinstance(restored.entry_points[0], EntryPoint)
    assert isinstance(restored.test_cases[0], TestCaseModel)
    assert isinstance(restored.scenarios[0], Scenario)
    assert isinstance(restored.coverage_matrix, CoverageMatrix)
    assert isinstance(restored.risk_assessment[0], RiskAssessment)
    assert restored.metadata == {"analyzer": "APIAnalyzer"}

def test_analysis_result_from_dict_tolerates_missing_lists():
    minimal = {
        "project_type": "library",
        "coverage_matrix": _matrix().to_dict(),
    }
    restored = AnalysisResult.from_dict(minimal)
    assert restored.entry_points == []
    assert restored.test_cases == []
    assert restored.scenarios == []
    assert restored.risk_assessment == []
    assert restored.metadata == {}
