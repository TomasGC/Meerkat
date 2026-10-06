#!/usr/bin/env python3
"""Tests for analyzers/api_analyzer.py: endpoint extraction per framework and API scenarios."""

import pytest

from analyzers.api_analyzer import APIAnalyzer
from bba.models import EntryPoint, EntryPointType, HTTPMethod, Language, ProjectInfo, ProjectType


def _info(*types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.UNKNOWN,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=".",
        project_types=list(types),
    )


def _write(root, name: str, content: str):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _summary(entry_points):
    return sorted((ep.metadata["method"], ep.metadata["path"], ep.framework) for ep in entry_points)


# ── can_analyze ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("project_type", [ProjectType.REST_API, ProjectType.GRAPHQL_API, ProjectType.GRPC_API])
def test_can_analyze_accepts_every_api_type(project_type):
    assert APIAnalyzer().can_analyze(_info(ProjectType.CLI_APP, project_type))


def test_can_analyze_rejects_non_api_project():
    assert not APIAnalyzer().can_analyze(_info(ProjectType.CLI_APP, ProjectType.SQL_PROJECT))


# ── extract_entry_points ──────────────────────────────────────────────────────


def test_extract_go_endpoints_reads_gin_and_mux_and_skips_unknown_verb(tmp_path):
    _write(
        tmp_path,
        "main.go",
        "package main\n\nfunc main() {\n"
        '    router.GET("/users/:id", getUser)\n'
        '    router.HandleFunc("/orders", list).Methods("POST")\n'
        '    router.HandleFunc("/weird", h).Methods("FETCH")\n'
        "}\n",
    )
    _write(tmp_path, "empty.go", "")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [("GET", "/users/:id", "gin"), ("POST", "/orders", "mux")]
    get_user = next(ep for ep in entry_points if ep.metadata["method"] == "GET")
    assert get_user.type == EntryPointType.HTTP_ENDPOINT
    assert get_user.name == "GET /users/:id"
    assert get_user.file_path == "main.go"
    assert get_user.line_number == 4
    assert [p.name for p in get_user.params] == ["id"]
    assert get_user.metadata["response_codes"]


def test_extract_typescript_endpoints_reads_express_routes(tmp_path):
    _write(
        tmp_path,
        "src/routes.ts",
        "const app = express();\napp.get('/api/posts/:id', h);\napp.delete('/api/posts/:id', h);\n",
    )
    _write(tmp_path, "src/empty.js", "")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("DELETE", "/api/posts/:id", "express"),
        ("GET", "/api/posts/:id", "express"),
    ]
    assert {ep.file_path.replace("\\", "/") for ep in entry_points} == {"src/routes.ts"}


def test_extract_csharp_endpoints_maps_attributes_and_defaults_empty_route_to_root(tmp_path):
    _write(
        tmp_path,
        "Controllers/UsersController.cs",
        '[HttpGet("")]\npublic IActionResult List() => Ok();\n'
        '[HttpPost("users/{id}")]\npublic IActionResult Create(int id) => Ok();\n'
        'app.MapDelete("/items/{id}", () => 1);\n',
    )
    _write(tmp_path, "Empty.cs", "")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("DELETE", "/items/{id}", "aspnet"),
        ("GET", "/", "aspnet"),
        ("POST", "users/{id}", "aspnet"),
    ]
    create = next(ep for ep in entry_points if ep.metadata["method"] == "POST")
    assert [p.name for p in create.params] == ["id"]


def test_extract_python_endpoints_reads_fastapi_and_flask(tmp_path):
    _write(
        tmp_path,
        "app.py",
        "@app.get('/items/{item_id}')\ndef get_item(item_id): ...\n\n"
        "@app.route('/login', methods=['POST'])\ndef login(): ...\n",
    )
    _write(tmp_path, "empty.py", "")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [("GET", "/items/{item_id}", "fastapi"), ("POST", "/login", "flask")]


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): py_django pattern has one capture group, so `method, path = match` unpacks a string and raises",
)
def test_extract_python_endpoints_handles_django_urlconf(tmp_path):
    _write(tmp_path, "urls.py", "urlpatterns = [\n    path('users/', views.users),\n]\n")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert [ep.metadata["path"] for ep in entry_points] == ["users/"]


def test_extract_java_endpoints_maps_spring_mappings(tmp_path):
    _write(
        tmp_path,
        "src/UserController.java",
        '@GetMapping("/users/{id}")\npublic User get() {}\n'
        '@PutMapping("/users/{id}")\npublic User put() {}\n'
        '@PatchMapping("/users")\npublic User patch() {}\n',
    )
    _write(tmp_path, "src/Empty.java", "")

    entry_points = APIAnalyzer().extract_entry_points(tmp_path)

    assert _summary(entry_points) == [
        ("GET", "/users/{id}", "spring"),
        ("PATCH", "/users", "spring"),
        ("PUT", "/users/{id}", "spring"),
    ]


def test_extract_entry_points_of_project_without_sources_is_empty(tmp_path):
    _write(tmp_path, "README.md", "# nothing here\n")

    assert APIAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_tests_returns_no_tests(sample_go_project):
    assert APIAnalyzer().parse_tests(sample_go_project) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def _http_entry(method: str, path: str) -> EntryPoint:
    return EntryPoint(
        type=EntryPointType.HTTP_ENDPOINT,
        name=f"{method} {path}",
        params=[],
        file_path="a.go",
        line_number=1,
        metadata={"method": method, "path": path},
    )


def test_generate_scenarios_emits_happy_error_and_security_per_endpoint():
    scenarios = APIAnalyzer().generate_scenarios([_http_entry("POST", "/users")])

    assert [(s.scenario_type, s.expected_output, s.input_combination["type"]) for s in scenarios] == [
        ("happy_path", 200, "valid"),
        ("error", 400, "missing_params"),
        ("security", 401, "unauthorized"),
    ]
    assert all(s.endpoint == "/users" and s.method == HTTPMethod.POST for s in scenarios)
    assert scenarios[0].description == "Valid POST request to /users"


def test_generate_scenarios_skips_entry_with_unknown_method():
    assert APIAnalyzer().generate_scenarios([_http_entry("FETCH", "/x")]) == []


def test_generate_scenarios_defaults_to_get_and_entry_name_without_metadata():
    entry = EntryPoint(type=EntryPointType.HTTP_ENDPOINT, name="/health", params=[], file_path="a", line_number=1)

    scenarios = APIAnalyzer().generate_scenarios([entry])

    assert {(s.endpoint, s.method) for s in scenarios} == {("/health", HTTPMethod.GET)}


def test_analyze_go_project_end_to_end(sample_go_project):
    result = APIAnalyzer().analyze(sample_go_project, _info(ProjectType.REST_API))

    assert len(result.entry_points) == 4
    assert len(result.scenarios) == 12
    assert result.coverage_matrix.tested_scenarios == 0
    assert result.risk_assessment[0].risk_level == "CRITICAL"
