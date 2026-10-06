#!/usr/bin/env python3
"""Tests for coverage_by_type.py — unit tests"""

import json

from bba.models import HTTPMethod, TestFramework
from coverage_by_type import (
    _load_scenarios,
    _load_tests,
    analyze_by_type,
    generate_markdown,
)


def test_load_scenarios_valid(sample_scenarios_json):
    scenarios = _load_scenarios(sample_scenarios_json)
    assert len(scenarios) == 5
    assert scenarios[0].endpoint == "/users/:id"
    assert scenarios[0].method == HTTPMethod.GET


def test_load_scenarios_non_http_method(temp_dir):
    data = {
        "scenarios": [
            {
                "endpoint": "MyWindow",
                "method": "RENDER",
                "input_combination": {},
                "expected_output": 200,
                "scenario_type": "happy_path",
                "description": "",
            }
        ]
    }
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
    data = {
        "tests": [
            {
                "name": "test_x",
                "file_path": "t.py",
                "line_number": 1,
                "framework": "vitest_custom",
                "tested_endpoint": "/x",
                "tested_method": "GET",
                "tested_inputs": [],
                "expected_outputs": [],
                "test_type": "unit",
            }
        ]
    }
    f = temp_dir / "t.json"
    f.write_text(json.dumps(data))
    tests = _load_tests(f)
    assert tests[0].framework == TestFramework.UNKNOWN


def test_load_tests_no_tested_method(temp_dir):
    data = {
        "tests": [
            {
                "name": "test_x",
                "file_path": "t.py",
                "line_number": 1,
                "framework": "pytest",
                "tested_inputs": [],
                "expected_outputs": [],
                "test_type": "unit",
            }
        ]
    }
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
    s_data = {
        "scenarios": [
            {
                "endpoint": "/x",
                "method": "GET",
                "input_combination": {},
                "expected_output": 200,
                "scenario_type": "happy_path",
                "description": "",
            }
        ]
    }
    t_data = {
        "tests": [
            {
                "name": "test_smoke",
                "file_path": "t.py",
                "line_number": 1,
                "framework": "pytest",
                "tested_endpoint": "/x",
                "tested_method": "GET",
                "tested_inputs": [],
                "expected_outputs": [],
                "test_type": "smoke",
            }
        ]
    }
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
    s_data = {
        "scenarios": [
            {
                "endpoint": "/y",
                "method": "DELETE",
                "input_combination": {},
                "expected_output": 204,
                "scenario_type": "happy_path",
                "description": "",
            }
        ]
    }
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
    s_data = {
        "scenarios": [
            {
                "endpoint": "/x",
                "method": "GET",
                "input_combination": {},
                "expected_output": 200,
                "scenario_type": "happy_path",
                "description": "",
            }
        ]
    }
    t_data = {
        "tests": [
            {
                "name": "test_x",
                "file_path": "t.py",
                "line_number": 1,
                "framework": "pytest",
                "tested_endpoint": "/x",
                "tested_method": "GET",
                "tested_inputs": [],
                "expected_outputs": [],
                "test_type": "unit",
            }
        ]
    }
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


def _scenario_dicts(n: int) -> list[dict]:
    return [
        {
            "endpoint": f"/r{i}",
            "method": "GET",
            "input_combination": {},
            "expected_output": 200,
            "scenario_type": "happy_path",
            "description": f"scenario {i}",
        }
        for i in range(n)
    ]


def test_load_tests_invalid_tested_method_becomes_none(temp_dir):
    data = {
        "tests": [{"name": "t", "file_path": "t.py", "line_number": 1, "framework": "pytest", "tested_method": "FETCH"}]
    }
    f = temp_dir / "t.json"
    f.write_text(json.dumps(data))
    assert _load_tests(f)[0].tested_method is None


def test_generate_markdown_lists_blind_spots_and_truncates_long_tables(temp_dir):
    sf = temp_dir / "s.json"
    sf.write_text(json.dumps({"scenarios": _scenario_dicts(105)}))
    result = analyze_by_type(_load_scenarios(sf), [])
    md = generate_markdown(result)
    assert "### Uncovered scenarios (105)" in md
    assert "*55 more rows omitted*" in md
    assert "## Absolute Blind Spots (105)" in md
    assert "| `GET /r0` | happy_path | scenario 0 |" in md
    assert "*5 more rows omitted*" in md


# ── main ──────────────────────────────────────────────────────────────────────


def _run_main(monkeypatch, *argv):
    import coverage_by_type

    monkeypatch.setattr("sys.argv", ["coverage_by_type.py", *map(str, argv)])
    return coverage_by_type.main()


def test_main_writes_json_and_markdown(sample_scenarios_json, sample_tests_json, temp_dir, monkeypatch, capsys):
    out = temp_dir / "breakdown.json"
    md = temp_dir / "breakdown.md"
    assert _run_main(monkeypatch, sample_scenarios_json, sample_tests_json, "-o", out, "-m", md) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["combined"]["total_scenarios"] == 5
    assert data["combined"]["total_tests"] == 4
    assert md.read_text(encoding="utf-8").startswith("# Coverage by Test Type")
    assert "Markdown written to" in capsys.readouterr().err


def test_main_library_mode_prints_json(sample_scenarios_json, sample_tests_json, monkeypatch, capsys):
    assert _run_main(monkeypatch, sample_scenarios_json, sample_tests_json, "--mode", "library") == 0
    assert set(json.loads(capsys.readouterr().out)) >= {"unit", "int_mock", "int_real", "e2e", "combined"}


def test_main_missing_file_returns_one(temp_dir, sample_tests_json, monkeypatch, capsys):
    assert _run_main(monkeypatch, temp_dir / "nope.json", sample_tests_json) == 1
    assert "[ERROR] File not found" in capsys.readouterr().err


def test_main_invalid_input_returns_one(temp_dir, sample_tests_json, monkeypatch, capsys):
    bad = temp_dir / "bad.json"
    bad.write_text(json.dumps({"scenarios": [{"endpoint": "/x"}]}))
    assert _run_main(monkeypatch, bad, sample_tests_json) == 1
    assert "[ERROR] Invalid input" in capsys.readouterr().err
