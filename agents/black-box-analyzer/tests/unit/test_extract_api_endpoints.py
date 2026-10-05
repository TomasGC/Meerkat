#!/usr/bin/env python3
"""Tests for extract_api_endpoints.py"""

import json

import pytest
from bba.models import HTTPMethod, Language
from extract_api_endpoints import (
    extract_csharp_endpoints,
    extract_endpoints,
    extract_go_endpoints,
    extract_java_endpoints,
    extract_params_from_path,
    extract_python_endpoints,
    extract_typescript_endpoints,
)

# Add scripts directory to path


def test_extract_params_from_path_colon_style():
    """Test parameter extraction from :param style."""
    params = extract_params_from_path("/users/:id")
    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].param_type == "path"


def test_extract_params_from_path_brace_style():
    """Test parameter extraction from {param} style."""
    params = extract_params_from_path("/users/{id}")
    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].param_type == "path"


def test_extract_params_from_path_multiple():
    """Test parameter extraction with multiple params."""
    params = extract_params_from_path("/posts/:postId/comments/:commentId")
    assert len(params) == 2
    assert params[0].name == "postId"
    assert params[1].name == "commentId"


def test_extract_params_from_path_mixed():
    """Test parameter extraction with mixed styles."""
    params = extract_params_from_path("/users/{userId}/posts/:postId")
    assert len(params) == 2
    assert {p.name for p in params} == {"userId", "postId"}


def test_extract_go_endpoints(sample_go_project):
    """Test Go endpoint extraction."""
    endpoints = extract_go_endpoints(sample_go_project)

    assert len(endpoints) == 4

    # Check GET endpoint
    get_endpoint = next(e for e in endpoints if e.method == HTTPMethod.GET)
    assert get_endpoint.path == "/users/:id"
    assert len(get_endpoint.params) == 1
    assert get_endpoint.params[0].name == "id"

    # Check POST endpoint
    post_endpoint = next(e for e in endpoints if e.method == HTTPMethod.POST)
    assert post_endpoint.path == "/users"


def test_extract_typescript_endpoints(sample_typescript_project):
    """Test TypeScript endpoint extraction."""
    endpoints = extract_typescript_endpoints(sample_typescript_project)

    assert len(endpoints) == 3

    # Check GET endpoint
    get_endpoint = next(e for e in endpoints if e.method == HTTPMethod.GET)
    assert get_endpoint.path == "/api/posts/:id"
    assert get_endpoint.framework == "express"

    # Check POST endpoint
    post_endpoint = next(e for e in endpoints if e.method == HTTPMethod.POST)
    assert post_endpoint.path == "/api/posts"


def test_extract_csharp_endpoints(sample_csharp_project):
    """Test C# endpoint extraction."""
    endpoints = extract_csharp_endpoints(sample_csharp_project)

    assert len(endpoints) == 3  # Actual: GET, PUT, DELETE

    # Check GET endpoint
    get_endpoint = next(e for e in endpoints if e.method == HTTPMethod.GET)
    assert "{id}" in get_endpoint.path
    assert get_endpoint.framework == "aspnet"


def test_extract_python_endpoints(sample_python_project):
    """Test Python endpoint extraction."""
    endpoints = extract_python_endpoints(sample_python_project)

    assert len(endpoints) == 4

    # Check GET endpoint
    get_endpoint = next(e for e in endpoints if e.method == HTTPMethod.GET)
    assert "/items/{item_id}" in get_endpoint.path

    # Check POST endpoint
    post_endpoint = next(e for e in endpoints if e.method == HTTPMethod.POST)
    assert post_endpoint.path == "/items"


def test_extract_endpoints_go(sample_go_project):
    """Test unified endpoint extraction for Go."""
    endpoints = extract_endpoints(sample_go_project, Language.GO)
    assert len(endpoints) == 4


def test_extract_endpoints_typescript(sample_typescript_project):
    """Test unified endpoint extraction for TypeScript."""
    endpoints = extract_endpoints(sample_typescript_project, Language.TYPESCRIPT)
    assert len(endpoints) == 3


def test_extract_endpoints_csharp(sample_csharp_project):
    """Test unified endpoint extraction for C#."""
    endpoints = extract_endpoints(sample_csharp_project, Language.CSHARP)
    assert len(endpoints) == 3  # Actual: GET, PUT, DELETE


def test_extract_endpoints_python(sample_python_project):
    """Test unified endpoint extraction for Python."""
    endpoints = extract_endpoints(sample_python_project, Language.PYTHON)
    assert len(endpoints) == 4


def test_extract_endpoints_auto_detect(sample_go_project):
    """Test endpoint extraction with auto language detection."""
    endpoints = extract_endpoints(sample_go_project)  # No language specified
    assert len(endpoints) == 4
    assert all(e.framework == "gin" for e in endpoints)


def _project(temp_dir, name: str, files: dict[str, str]):
    root = temp_dir / name
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def test_extract_go_mux_reads_path_then_method(temp_dir):
    root = _project(
        temp_dir,
        "mux",
        {
            "main.go": 'router.HandleFunc("/orders/{id}", getOrder).Methods("GET")\n',
            "empty.go": "",
        },
    )
    endpoints = extract_go_endpoints(root)
    assert [(e.path, e.method, e.framework) for e in endpoints] == [("/orders/{id}", HTTPMethod.GET, "mux")]
    assert endpoints[0].params[0].name == "id"


def test_extract_typescript_skips_empty_files(temp_dir):
    root = _project(temp_dir, "ts", {"empty.ts": "", "app.ts": "fastify.get('/health', h)\n"})
    endpoints = extract_typescript_endpoints(root)
    assert [(e.path, e.framework) for e in endpoints] == [("/health", "fastify")]


def test_extract_csharp_empty_route_defaults_to_root(temp_dir):
    root = _project(temp_dir, "cs", {"Empty.cs": "", "C.cs": '[HttpGet("")]\npublic IActionResult List() => Ok();\n'})
    endpoints = extract_csharp_endpoints(root)
    assert [(e.path, e.method) for e in endpoints] == [("/", HTTPMethod.GET)]


def test_extract_csharp_minimal_api(temp_dir):
    root = _project(temp_dir, "min", {"Program.cs": 'app.MapPost("/todos", Create);\n'})
    endpoints = extract_csharp_endpoints(root)
    assert [(e.path, e.method, e.framework) for e in endpoints] == [("/todos", HTTPMethod.POST, "aspnet")]


def test_extract_python_flask_reads_path_then_method(temp_dir):
    root = _project(
        temp_dir,
        "flask",
        {"empty.py": "", "app.py": "@app.route('/login', methods=['POST'])\ndef login(): pass\n"},
    )
    endpoints = extract_python_endpoints(root)
    assert [(e.path, e.method, e.framework) for e in endpoints] == [("/login", HTTPMethod.POST, "flask")]


@pytest.mark.xfail(
    strict=True,
    reason="bug (#50): py_django pattern has one capture group, so `method, path = match` unpacks a string",
)
def test_extract_python_django_path_does_not_crash(temp_dir):
    root = _project(temp_dir, "django", {"urls.py": "urlpatterns = [path('users/', views.users)]\n"})
    endpoints = extract_python_endpoints(root)
    assert any(e.path == "users/" for e in endpoints)


def test_extract_java_spring_maps_annotations_to_methods(temp_dir):
    root = _project(
        temp_dir,
        "spring",
        {
            "Empty.java": "",
            "UserController.java": (
                '@GetMapping("/users/{id}")\npublic User get() {}\n'
                '@PostMapping("/users")\npublic User create() {}\n'
                '@DeleteMapping("/users/{id}")\npublic void delete() {}\n'
            ),
        },
    )
    endpoints = extract_java_endpoints(root)
    assert sorted((e.method.value, e.path) for e in endpoints) == [
        ("DELETE", "/users/{id}"),
        ("GET", "/users/{id}"),
        ("POST", "/users"),
    ]
    assert {e.framework for e in endpoints} == {"spring"}


def test_extract_endpoints_routes_java(temp_dir):
    root = _project(temp_dir, "spring2", {"A.java": '@PutMapping("/a")\nvoid a() {}\n'})
    assert [e.method for e in extract_endpoints(root, Language.JAVA)] == [HTTPMethod.PUT]


def test_extract_endpoints_unsupported_language_returns_empty(temp_dir):
    root = _project(temp_dir, "rust", {"main.rs": "fn main() {}\n"})
    assert extract_endpoints(root, Language.RUST) == []


# ── main ──────────────────────────────────────────────────────────────────────


def test_main_writes_endpoint_json(sample_go_project, temp_dir, monkeypatch):
    import extract_api_endpoints

    out = temp_dir / "endpoints.json"
    monkeypatch.setattr("sys.argv", ["x", str(sample_go_project), "--language", "go", "--output", str(out)])
    assert extract_api_endpoints.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["endpoint_count"] == 4
    assert {e["method"] for e in data["endpoints"]} == {"GET", "POST", "PUT", "DELETE"}


def test_main_auto_detects_language_and_prints(sample_python_project, monkeypatch, capsys):
    import extract_api_endpoints

    monkeypatch.setattr("sys.argv", ["x", str(sample_python_project)])
    assert extract_api_endpoints.main() == 0
    assert json.loads(capsys.readouterr().out)["endpoint_count"] == 4


def test_main_missing_path_returns_one(temp_dir, monkeypatch, capsys):
    import extract_api_endpoints

    monkeypatch.setattr("sys.argv", ["x", str(temp_dir / "missing"), "--language", "go"])
    assert extract_api_endpoints.main() == 1
    assert "Error: Path not found" in capsys.readouterr().err
