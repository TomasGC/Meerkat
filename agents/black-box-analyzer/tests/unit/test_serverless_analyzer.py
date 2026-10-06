#!/usr/bin/env python3
"""Tests for analyzers/event_driven/serverless_analyzer.py: Lambda, Azure Functions, Cloud Functions."""

from pathlib import Path

from analyzers.event_driven.serverless_analyzer import ServerlessAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, ProjectInfo, ProjectType


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


def test_can_analyze_accepts_only_serverless_projects(tmp_path):
    assert ServerlessAnalyzer().can_analyze(_info(tmp_path, ProjectType.SERVERLESS))
    assert not ServerlessAnalyzer().can_analyze(_info(tmp_path, ProjectType.BACKGROUND_WORKER))


# ── AWS Lambda ────────────────────────────────────────────────────────────────


def test_python_lambda_handler(tmp_path):
    _write(tmp_path, "handler.py", "import json\n\ndef lambda_handler(event, context):\n    return {}\n")

    handler = _by_name(ServerlessAnalyzer().extract_entry_points(tmp_path))["lambda_handler"]

    assert handler.type == EntryPointType.LAMBDA_HANDLER
    assert handler.line_number == 3
    assert handler.metadata == {"runtime": "python", "handler_type": "function"}
    assert [p.name for p in handler.params] == ["event", "context"]


def test_node_lambda_handler_export(tmp_path):
    _write(tmp_path, "index.js", "exports.handler = async (event, context) => ({})\n")

    handler = _by_name(ServerlessAnalyzer().extract_entry_points(tmp_path))["handler"]

    assert handler.metadata == {"runtime": "nodejs", "handler_type": "export"}
    assert handler.params[0].data_type == "object"


def test_go_lambda_handler_falls_back_to_default_name(tmp_path):
    _write(
        tmp_path,
        "main.go",
        "package main\n\nfunc handler(ctx context.Context, e events.APIGatewayProxyRequest) error { return nil }\n",
    )

    eps = [ep for ep in ServerlessAnalyzer().extract_entry_points(tmp_path) if ep.metadata.get("runtime") == "go"]

    assert [(ep.name, ep.line_number) for ep in eps] == [("handler", 3)]
    assert [p.data_type for p in eps[0].params] == ["context.Context", "events.Event"]


# ── Azure Functions ───────────────────────────────────────────────────────────


def test_python_azure_function_decorator_names_the_following_def(tmp_path):
    _write(
        tmp_path,
        "function_app.py",
        "app = func.FunctionApp()\n\n@app.route(route='hello')\ndef hello(req):\n    return 'hi'\n",
    )

    fn = _by_name(ServerlessAnalyzer().extract_entry_points(tmp_path))["hello"]

    assert fn.type == EntryPointType.FUNCTION_HANDLER
    assert fn.framework == "azure_functions"
    assert fn.line_number == 4
    assert fn.params[0].data_type == "HttpRequest"


def test_azure_decorator_without_nearby_def_is_ignored(tmp_path):
    _write(tmp_path, "function_app.py", "@app.route(route='x')\n" + "pass\n" * 100)

    assert ServerlessAnalyzer().extract_entry_points(tmp_path) == []


def test_csharp_function_name_attribute(tmp_path):
    _write(
        tmp_path,
        "Functions.cs",
        'public static class Functions {\n  [FunctionName("ProcessOrder")]\n  public static void Run() {}\n}\n',
    )

    fn = _by_name(ServerlessAnalyzer().extract_entry_points(tmp_path))["ProcessOrder"]

    assert fn.metadata == {"runtime": "csharp", "trigger": "http"}
    assert fn.line_number == 2


# ── Google Cloud Functions ────────────────────────────────────────────────────


def test_python_cloud_function_decorator(tmp_path):
    _write(
        tmp_path, "main.py", "import functions_framework\n\n@functions_framework.http\ndef greet(request):\n    pass\n"
    )

    fn = _by_name(ServerlessAnalyzer().extract_entry_points(tmp_path))["greet"]

    assert fn.framework == "google_cloud_functions"
    assert fn.params[0].name == "request"
    assert fn.line_number == 4


def test_gcp_decorator_without_def_is_ignored(tmp_path):
    _write(tmp_path, "main.py", "@functions_framework.http\n" + "x = 1\n" * 100)

    assert ServerlessAnalyzer().extract_entry_points(tmp_path) == []


def test_node_cloud_function_export(tmp_path):
    _write(tmp_path, "index.js", "exports.helloHttp = (req, res) => { res.send('ok') }\n")

    eps = ServerlessAnalyzer().extract_entry_points(tmp_path)

    gcp = [ep for ep in eps if ep.framework == "google_cloud_functions"]
    assert [ep.name for ep in gcp] == ["helloHttp"]
    assert [p.name for p in gcp[0].params] == ["req", "res"]


def test_empty_sources_yield_nothing(tmp_path):
    for name in ("a.py", "b.js", "c.ts", "d.go", "e.cs"):
        _write(tmp_path, name, "")

    assert ServerlessAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_tests_returns_no_tests(tmp_path):
    assert ServerlessAnalyzer().parse_tests(tmp_path) == []
