#!/usr/bin/env python3
"""Tests for diff_analysis.py — unit tests"""

import json
from pathlib import Path

import pytest

from diff_analysis import (
    AnalysisDiff,
    compare_analyses,
    format_markdown,
    format_summary,
    load_analysis,
)

def _make_analysis(coverage: float, untested: int, critical: int = 0, high: int = 0,
                   by_endpoint: dict | None = None) -> dict:
    return {
        "coverage_summary": {
            "coverage_percent": coverage,
            "untested_scenarios": untested,
            "by_endpoint": by_endpoint or {},
        },
        "risk_summary": {
            "by_level": {"CRITICAL": critical, "HIGH": high},
        },
    }

def test_load_analysis_valid(temp_dir):
    data = {"coverage_summary": {"coverage_percent": 42.0}}
    f = temp_dir / "analysis.json"
    f.write_text(json.dumps(data))
    result = load_analysis(f)
    assert result["coverage_summary"]["coverage_percent"] == 42.0

def test_load_analysis_missing_file(temp_dir):
    with pytest.raises(FileNotFoundError):
        load_analysis(temp_dir / "nonexistent.json")

def test_load_analysis_invalid_json(temp_dir):
    f = temp_dir / "bad.json"
    f.write_text("not json {{{")
    with pytest.raises(ValueError):
        load_analysis(f)

def test_compare_coverage_improved():
    baseline = _make_analysis(50.0, 10)
    current = _make_analysis(75.0, 5)
    diff = compare_analyses(baseline, current)
    assert diff.coverage_delta == pytest.approx(25.0)
    assert diff.new_coverage == 75.0
    assert diff.resolved_gaps == 5
    assert diff.new_gaps == 0

def test_compare_coverage_regressed():
    baseline = _make_analysis(80.0, 3)
    current = _make_analysis(60.0, 8)
    diff = compare_analyses(baseline, current)
    assert diff.coverage_delta == pytest.approx(-20.0)
    assert diff.resolved_gaps == 0
    assert diff.new_gaps == 5

def test_compare_critical_risk_change():
    baseline = _make_analysis(50.0, 5, critical=1, high=2)
    current = _make_analysis(60.0, 3, critical=3, high=1)
    diff = compare_analyses(baseline, current)
    assert diff.old_critical == 1
    assert diff.new_critical == 3
    assert diff.old_high == 2
    assert diff.new_high == 1

def test_compare_endpoint_improved():
    baseline = _make_analysis(50.0, 5, by_endpoint={"/users": {"coverage_percent": 40.0}})
    current = _make_analysis(70.0, 2, by_endpoint={"/users": {"coverage_percent": 90.0}})
    diff = compare_analyses(baseline, current)
    assert len(diff.improved_endpoints) == 1
    assert diff.improved_endpoints[0]["endpoint"] == "/users"
    assert diff.improved_endpoints[0]["delta"] == pytest.approx(50.0)

def test_compare_endpoint_regressed():
    baseline = _make_analysis(70.0, 2, by_endpoint={"/orders": {"coverage_percent": 80.0}})
    current = _make_analysis(50.0, 5, by_endpoint={"/orders": {"coverage_percent": 30.0}})
    diff = compare_analyses(baseline, current)
    assert len(diff.regressed_endpoints) == 1
    assert diff.regressed_endpoints[0]["delta"] == pytest.approx(-50.0)

def test_compare_new_and_removed_endpoints():
    baseline = _make_analysis(50.0, 5, by_endpoint={"/old": {"coverage_percent": 50.0}})
    current = _make_analysis(50.0, 5, by_endpoint={"/new": {"coverage_percent": 50.0}})
    diff = compare_analyses(baseline, current)
    assert "/new" in diff.new_endpoints
    assert "/old" in diff.removed_endpoints

def test_compare_empty_analyses():
    diff = compare_analyses({}, {})
    assert diff.coverage_delta == 0.0
    assert diff.resolved_gaps == 0
    assert diff.new_gaps == 0

def test_compare_uses_by_entry_point_fallback():
    baseline = {"coverage_summary": {"coverage_percent": 40.0, "untested_scenarios": 5,
                                      "by_entry_point": {"/ep": {"coverage_percent": 20.0}}},
                "risk_summary": {"by_level": {}}}
    current = {"coverage_summary": {"coverage_percent": 80.0, "untested_scenarios": 1,
                                     "by_entry_point": {"/ep": {"coverage_percent": 90.0}}},
               "risk_summary": {"by_level": {}}}
    diff = compare_analyses(baseline, current)
    assert len(diff.improved_endpoints) == 1

def test_to_dict_trend_improved():
    diff = compare_analyses(_make_analysis(40.0, 5), _make_analysis(60.0, 3))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "improved"

def test_to_dict_trend_regressed():
    diff = compare_analyses(_make_analysis(60.0, 3), _make_analysis(40.0, 7))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "regressed"

def test_to_dict_trend_unchanged():
    diff = compare_analyses(_make_analysis(50.0, 5), _make_analysis(50.0, 5))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "unchanged"

def test_format_markdown_has_headers():
    diff = compare_analyses(_make_analysis(40.0, 5), _make_analysis(60.0, 3))
    md = format_markdown(diff)
    assert "# Analysis Comparison Report" in md
    assert "Coverage Summary" in md
    assert "Gap Summary" in md

def test_format_summary_shows_regression():
    baseline = _make_analysis(80.0, 2, by_endpoint={"/x": {"coverage_percent": 80.0}})
    current = _make_analysis(60.0, 5, by_endpoint={"/x": {"coverage_percent": 20.0}})
    diff = compare_analyses(baseline, current)
    summary = format_summary(diff)
    assert "Regressions" in summary or "egressed" in summary
