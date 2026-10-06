#!/usr/bin/env python3
"""Tests for analyzers/llm_analyzer.py: LangChain/CrewAI extraction and scenario generation."""

from pathlib import Path

import pytest

from analyzers.llm_analyzer import LLMAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, Parameter, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.PYTHON,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_name(entry_points: list[EntryPoint]) -> dict[str, EntryPoint]:
    return {ep.name: ep for ep in entry_points}


def test_can_analyze_accepts_only_llm_agent_projects(tmp_path):
    assert LLMAnalyzer().can_analyze(_info(tmp_path, ProjectType.LLM_AI_AGENT))
    assert not LLMAnalyzer().can_analyze(_info(tmp_path, ProjectType.CLI_APP))


# ── LangChain ─────────────────────────────────────────────────────────────────


def test_langchain_tool_decorator_parses_typed_and_default_params(tmp_path):
    _write(tmp_path, "tools.py", "@tool\ndef search(query: str, limit: int = 5, raw):\n    pass\n")

    tool = _by_name(LLMAnalyzer().extract_entry_points(tmp_path))["search"]

    assert tool.type == EntryPointType.AGENT_TOOL
    assert tool.metadata == {"tool_type": "function"}
    assert [(p.name, p.data_type, p.required, p.default_value) for p in tool.params] == [
        ("query", "str", True, None),
        ("limit", "int", False, "5"),
        ("raw", "any", True, None),
    ]


def test_langchain_tool_trailing_comma_adds_no_param(tmp_path):
    _write(tmp_path, "tools.py", "@tool\ndef echo(text: str,):\n    pass\n")

    tool = _by_name(LLMAnalyzer().extract_entry_points(tmp_path))["echo"]

    assert [p.name for p in tool.params] == ["text"]


def test_langchain_tool_without_params_has_none(tmp_path):
    _write(tmp_path, "tools.py", "@tool\ndef now():\n    pass\n")

    assert _by_name(LLMAnalyzer().extract_entry_points(tmp_path))["now"].params == []


def test_langchain_basetool_class_agent_executor_and_prompt(tmp_path):
    _write(
        tmp_path,
        "agent.py",
        "class WeatherTool(BaseTool):\n    pass\n\n"
        "executor = AgentExecutor(agent=planner, tools=[])\n"
        'summary_prompt = PromptTemplate(input_variables=["x"], template="Summarize {x}")\n',
    )

    eps = _by_name(LLMAnalyzer().extract_entry_points(tmp_path))

    assert eps["WeatherTool"].metadata == {"tool_type": "class"}
    assert eps["planner"].type == EntryPointType.AGENT_WORKFLOW
    assert eps["planner"].metadata == {"workflow_type": "agent_executor"}
    prompt = next(ep for ep in eps.values() if ep.type == EntryPointType.PROMPT_TEMPLATE)
    assert prompt.line_number == 5
    assert prompt.metadata == {"template_content": "Summarize {x}"}


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): "
    "the variable name is searched in the 100 chars before the match, which never contain PromptTemplate",
)
def test_prompt_template_is_named_after_its_variable(tmp_path):
    _write(tmp_path, "p.py", "summary_prompt = PromptTemplate(template='Summarize')\n")

    names = [ep.name for ep in LLMAnalyzer().extract_entry_points(tmp_path)]

    assert names == ["summary_prompt"]


def test_prompt_template_without_assignment_gets_default_name(tmp_path):
    _write(tmp_path, "p.py", "chain(PromptTemplate(template='Hi'))\n")

    eps = LLMAnalyzer().extract_entry_points(tmp_path)

    assert [(ep.name, ep.type) for ep in eps] == [("prompt_template", EntryPointType.PROMPT_TEMPLATE)]


def test_empty_python_files_yield_nothing(tmp_path):
    _write(tmp_path, "empty.py", "")

    assert LLMAnalyzer().extract_entry_points(tmp_path) == []


# ── CrewAI ────────────────────────────────────────────────────────────────────


def test_crewai_agent_and_task_decorators(tmp_path):
    _write(tmp_path, "crew.py", "@agent\ndef researcher(self):\n    pass\n\n@task\ndef research(self):\n    pass\n")

    eps = _by_name(LLMAnalyzer().extract_entry_points(tmp_path))

    assert eps["researcher"].metadata == {"component_type": "agent"}
    assert eps["research"].metadata == {"component_type": "task"}
    assert eps["research"].line_number == 5
    assert {eps["researcher"].framework, eps["research"].framework} == {"crewai"}


def test_parse_tests_returns_no_tests(tmp_path):
    assert LLMAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def test_scenarios_per_entry_point_type():
    eps = [
        EntryPoint(EntryPointType.AGENT_TOOL, "search", [Parameter("q", "arg", "str")], "t.py", 1),
        EntryPoint(EntryPointType.AGENT_WORKFLOW, "planner", [], "a.py", 1),
        EntryPoint(EntryPointType.PROMPT_TEMPLATE, "summary", [], "p.py", 1),
        EntryPoint(EntryPointType.COMPONENT, "ignored", [], "x.py", 1),
    ]

    scenarios = LLMAnalyzer().generate_scenarios(eps)

    assert [(s.endpoint, s.method_name, s.scenario_type) for s in scenarios] == [
        ("search", "TOOL", "happy_path"),
        ("search", "TOOL", "error"),
        ("search", "TOOL", "edge_case"),
        ("planner", "WORKFLOW", "happy_path"),
        ("planner", "WORKFLOW", "error"),
        ("summary", "PROMPT", "happy_path"),
        ("summary", "PROMPT", "error"),
    ]
    assert scenarios[0].input_combination == {"params": {"q": "valid_value"}}
