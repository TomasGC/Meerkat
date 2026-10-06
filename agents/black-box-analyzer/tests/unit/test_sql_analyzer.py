#!/usr/bin/env python3
"""Tests for analyzers/sql_analyzer.py: SQL parameter parsing and scenario generation."""

import pytest

from analyzers.sql_analyzer import SQLAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, Parameter, ProjectInfo, ProjectType


def _info(*types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.SQL,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=".",
        project_types=list(types),
    )


def test_can_analyze_only_sql_projects():
    assert SQLAnalyzer().can_analyze(_info(ProjectType.SQL_PROJECT))
    assert not SQLAnalyzer().can_analyze(_info(ProjectType.REST_API))


# ── extraction ────────────────────────────────────────────────────────────────


def test_extract_entry_points_reads_procedures_functions_and_triggers(tmp_path):
    (tmp_path / "schema.sql").write_text(
        "CREATE PROCEDURE add_user(@name VARCHAR, @age INT)\nAS BEGIN END;\n\n"
        "CREATE OR REPLACE FUNCTION total() RETURNS INT AS $$ SELECT 1 $$;\n\n"
        "CREATE TRIGGER audit_users AFTER INSERT ON users;\n",
        encoding="utf-8",
    )
    (tmp_path / "empty.sql").write_text("", encoding="utf-8")

    entry_points = SQLAnalyzer().extract_entry_points(tmp_path)

    assert sorted((ep.type.value, ep.name, ep.line_number) for ep in entry_points) == [
        ("sql_function", "total", 4),
        ("sql_trigger", "audit_users", 6),
        ("stored_procedure", "add_user", 1),
    ]
    proc = next(ep for ep in entry_points if ep.name == "add_user")
    assert [(p.name, p.data_type) for p in proc.params] == [("name", "varchar"), ("age", "int")]


def test_parse_sql_params_skips_blank_and_unparseable_entries():
    params = SQLAnalyzer()._parse_sql_params("@id INT, , garbage")

    assert [(p.name, p.param_type, p.data_type, p.required) for p in params] == [("id", "sql_param", "int", True)]


def test_parse_sql_params_of_empty_string_is_empty():
    assert SQLAnalyzer()._parse_sql_params("   ") == []


def test_parse_sql_params_strips_in_and_out_direction():
    params = SQLAnalyzer()._parse_sql_params("IN user_id INT, OUT total NUMERIC")

    assert [(p.name, p.data_type) for p in params] == [("user_id", "int"), ("total", "numeric")]


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): direction regex tries IN before INOUT, so 'INOUT x INT' parses as name 'OUT', type 'x'",
)
def test_parse_sql_params_strips_inout_direction():
    params = SQLAnalyzer()._parse_sql_params("INOUT counter INT")

    assert [(p.name, p.data_type) for p in params] == [("counter", "int")]


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): "
    "unanchored optional IN/OUT prefix eats the start of a name, so 'invoice_id INT' becomes 'voice_id'",
)
def test_parse_sql_params_keeps_names_starting_with_in():
    params = SQLAnalyzer()._parse_sql_params("invoice_id INT")

    assert [p.name for p in params] == ["invoice_id"]


def test_parse_tests_returns_no_tests(tmp_path):
    assert SQLAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def _entry(entry_type: EntryPointType, name: str, params=()) -> EntryPoint:
    return EntryPoint(type=entry_type, name=name, params=list(params), file_path="s.sql", line_number=1)


def _param(name: str, data_type: str) -> Parameter:
    return Parameter(name=name, param_type="sql_param", data_type=data_type)


def test_procedure_scenarios_cover_valid_null_empty_negative_and_missing_params():
    proc = _entry(EntryPointType.STORED_PROCEDURE, "add_user", [_param("name", "varchar"), _param("age", "int")])

    scenarios = SQLAnalyzer().generate_scenarios([proc])

    assert [(s.scenario_type, s.input_combination, s.expected_output) for s in scenarios] == [
        ("happy_path", {"params": {"name": "valid_value", "age": "valid_value"}}, 0),
        ("edge_case", {"params": {"name": None}}, 0),
        ("edge_case", {"params": {"age": None}}, 0),
        ("edge_case", {"params": {"name": ""}}, 0),
        ("edge_case", {"params": {"age": -1}}, 0),
        ("error", {"params": {}}, 1),
    ]
    assert {s.method for s in scenarios} == {"EXECUTE"}


def test_function_without_params_gets_only_the_happy_path():
    scenarios = SQLAnalyzer().generate_scenarios([_entry(EntryPointType.SQL_FUNCTION, "total")])

    assert [(s.scenario_type, s.description) for s in scenarios] == [("happy_path", "Execute total with valid params")]


def test_trigger_gets_one_scenario_per_dml_operation():
    scenarios = SQLAnalyzer().generate_scenarios([_entry(EntryPointType.SQL_TRIGGER, "audit")])

    assert [(s.method, s.input_combination) for s in scenarios] == [
        ("INSERT", {"operation": "insert"}),
        ("UPDATE", {"operation": "update"}),
        ("DELETE", {"operation": "delete"}),
    ]


def test_non_sql_entry_points_get_no_scenarios():
    assert SQLAnalyzer().generate_scenarios([_entry(EntryPointType.COMPONENT, "X")]) == []


def test_analyze_sql_project_reports_untested_procedures(tmp_path):
    (tmp_path / "p.sql").write_text("CREATE PROC get_order(@id INT)\nAS SELECT 1;\n", encoding="utf-8")

    result = SQLAnalyzer().analyze(tmp_path, _info(ProjectType.SQL_PROJECT))

    assert [ep.name for ep in result.entry_points] == ["get_order"]
    assert result.coverage_matrix.total_scenarios == 4
    assert result.coverage_matrix.tested_scenarios == 0
    assert len(result.risk_assessment) == 4
