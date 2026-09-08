#!/usr/bin/env python3
"""Tests for coverage_by_type.py — unit tests"""

import json
from pathlib import Path

from coverage_by_type import (
    _load_scenarios,
    _load_tests,
    analyze_by_type,
    generate_markdown,
)
from common.models import HTTPMethod, TestFramework

def test_load_scenarios_valid(sample_scenarios_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    assert len(scenarios) == 5
    assert scenarios[0].endpoint == "/users/:id"
    assert scenarios[0].method == HTTPMethod.GET

def test_load_scenarios_non_http_method(temp_dir):
    data = {"scenarios": [
        {"endpoint": "MyWindow", "method": "RENDER",
         "input_combination": {}, "expected_output": 200,
         "scenario_type": "happy_path", "description": ""}
    ]}
    f = temp_dir / "s.json"
    f.write_text(json.dumps(data))
    scenarios = _load_scenarios(f)
    assert len(scenarios) == 1
    assert scenarios[0].method == HTTPMethod.GET

def test_load_scenarios_empty_file(temp_dir):
    f = temp_dir / "s.json"
    f.write_text(json.dumps({"scenarios": []}))
    assert _load_scenarios(f) == []

def test_load_tests_valid(sample_tests_json):
    tests = _load_tests(sample_tests_json)
    assert len(tests) == 4
    assert tests[0].name == "TestGetUser"
    assert tests[0].test_type == "unit"

def test_load_tests_unknown_framework(temp_dir):
    data = {"tests": [
        {"name": "test_x", "file_path": "t.py", "line_number": 1,
         "framework": "vitest_custom", "tested_endpoint": "/x",
         "tested_method": "GET", "tested_inputs": [], "expected_outputs": [],
         "test_type": "unit"}
    ]}
    f = temp_dir / "t.json"
    f.write_text(json.dumps(data))
    tests = _load_tests(f)
    assert tests[0].framework == TestFramework.UNKNOWN

def test_load_tests_no_tested_method(temp_dir):
    data = {"tests": [
        {"name": "test_x", "file_path": "t.py", "line_number": 1,
         "framework": "pytest", "tested_inputs": [], "expected_outputs": [],
         "test_type": "unit"}
    ]}
    f = temp_dir / "t.json"
    f.write_text(json.dumps(data))
    tests = _load_tests(f)
    assert tests[0].tested_method is None

def test_analyze_by_type_returns_all_tiers(sample_scenarios_json, sample_tests_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    tests = _load_tests(sample_tests_json)
    result = analyze_by_type(scenarios, tests)
    for tier in ("unit", "int_mock", "int_real", "e2e"):
        assert tier in result
    assert "combined" in result
    assert "unknown" in result

def test_analyze_by_type_unknown_tier_bucket(temp_dir):
    s_data = {"scenarios": [
        {"endpoint": "/x", "method": "GET", "input_combination": {},
         "expected_output": 200, "scenario_type": "happy_path", "description": ""}
    ]}
    t_data = {"tests": [
        {"name": "test_smoke", "file_path": "t.py", "line_number": 1,
         "framework": "pytest", "tested_endpoint": "/x", "tested_method": "GET",
         "tested_inputs": [], "expected_outputs": [], "test_type": "smoke"}
    ]}
    sf = temp_dir / "s.json"
    tf = temp_dir / "t.json"
    sf.write_text(json.dumps(s_data))
    tf.write_text(json.dumps(t_data))
    result = analyze_by_type(_load_scenarios(sf), _load_tests(tf))
    assert result["unknown"]["test_count"] == 1

def test_analyze_by_type_empty_scenarios(sample_tests_json, temp_dir):
    sf = temp_dir / "s.json"
    sf.write_text(json.dumps({"scenarios": []}))
    tests = _load_tests(sample_tests_json)
    result = analyze_by_type([], tests)
    assert result["combined"]["total_scenarios"] == 0
    assert result["combined"]["absolute_blind_spot_percent"] == 0.0

def test_analyze_by_type_combined_blind_spot(temp_dir):
    s_data = {"scenarios": [
        {"endpoint": "/y", "method": "DELETE", "input_combination": {},
         "expected_output": 204, "scenario_type": "happy_path", "description": ""}
    ]}
    t_data = {"tests": []}
    sf = temp_dir / "s.json"
    tf = temp_dir / "t.json"
    sf.write_text(json.dumps(s_data))
    tf.write_text(json.dumps(t_data))
    result = analyze_by_type(_load_scenarios(sf), _load_tests(tf))
    assert result["combined"]["absolute_blind_spots"] == 1
    assert len(result["combined"]["blind_spots"]) == 1

def test_analyze_by_type_coverage_percent(sample_scenarios_json, sample_tests_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    tests = _load_tests(sample_tests_json)
    result = analyze_by_type(scenarios, tests)
    assert 0.0 <= result["unit"]["coverage_percent"] <= 100.0

def test_generate_markdown_has_expected_headers(sample_scenarios_json, sample_tests_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    tests = _load_tests(sample_tests_json)
    result = analyze_by_type(scenarios, tests)
    md = generate_markdown(result)
    assert "# Coverage by Test Type" in md
    assert "## Summary" in md
    assert "## UNIT" in md
    assert "## INT MOCK" in md

def test_generate_markdown_empty_tier_shows_covered(temp_dir):
    s_data = {"scenarios": [
        {"endpoint": "/x", "method": "GET", "input_combination": {},
         "expected_output": 200, "scenario_type": "happy_path", "description": ""}
    ]}
    t_data = {"tests": [
        {"name": "test_x", "file_path": "t.py", "line_number": 1,
         "framework": "pytest", "tested_endpoint": "/x", "tested_method": "GET",
         "tested_inputs": [], "expected_outputs": [], "test_type": "unit"}
    ]}
    sf = temp_dir / "s.json"
    tf = temp_dir / "t.json"
    sf.write_text(json.dumps(s_data))
    tf.write_text(json.dumps(t_data))
    result = analyze_by_type(_load_scenarios(sf), _load_tests(tf))
    md = generate_markdown(result)
    assert "All scenarios covered by this tier" in md

def test_generate_markdown_progress_bar(sample_scenarios_json, sample_tests_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    tests = _load_tests(sample_tests_json)
    result = analyze_by_type(scenarios, tests)
    md = generate_markdown(result)
    assert "█" in md or "░" in md
