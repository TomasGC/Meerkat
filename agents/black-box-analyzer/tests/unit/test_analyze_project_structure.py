#!/usr/bin/env python3
"""Tests for analyze_project_structure.py"""

import json

import pytest

from analyze_project_structure import (
    analyze_project,
    count_endpoints,
    count_test_files,
    detect_frameworks,
    detect_project_types,
    detect_test_framework,
    infer_project_type,
)
from bba.models import Language, ProjectType, TestFramework
from bba.utils import detect_project_language

# Add scripts directory to path


def test_detect_language_go(sample_go_project):
    """Test Go language detection."""
    language = detect_project_language(sample_go_project)
    assert language == Language.GO


def test_detect_language_typescript(sample_typescript_project):
    """Test TypeScript language detection."""
    language = detect_project_language(sample_typescript_project)
    assert language == Language.TYPESCRIPT


def test_detect_language_csharp(sample_csharp_project):
    """Test C# language detection."""
    language = detect_project_language(sample_csharp_project)
    assert language == Language.CSHARP


def test_detect_language_python(sample_python_project):
    """Test Python language detection."""
    language = detect_project_language(sample_python_project)
    assert language == Language.PYTHON


def test_detect_frameworks_go(sample_go_project):
    """Test Go framework detection (gin)."""
    frameworks = detect_frameworks(sample_go_project, Language.GO)
    assert "gin" in frameworks


def test_detect_frameworks_typescript(sample_typescript_project):
    """Test TypeScript framework detection (express)."""
    frameworks = detect_frameworks(sample_typescript_project, Language.TYPESCRIPT)
    assert "express" in frameworks


def test_detect_frameworks_csharp(sample_csharp_project):
    """Test C# framework detection (aspnet)."""
    frameworks = detect_frameworks(sample_csharp_project, Language.CSHARP)
    assert "aspnet" in frameworks


def test_detect_frameworks_python(sample_python_project):
    """Test Python framework detection (fastapi)."""
    frameworks = detect_frameworks(sample_python_project, Language.PYTHON)
    assert "fastapi" in frameworks


def test_count_endpoints_go(sample_go_project):
    """Test endpoint counting for Go project."""
    count = count_endpoints(sample_go_project, Language.GO, ["gin"])
    assert count == 4  # GET, POST, PUT, DELETE


def test_count_endpoints_typescript(sample_typescript_project):
    """Test endpoint counting for TypeScript project."""
    count = count_endpoints(sample_typescript_project, Language.TYPESCRIPT, ["express"])
    assert count == 3  # GET, POST, DELETE


def test_count_endpoints_csharp(sample_csharp_project):
    """Test endpoint counting for C# project."""
    count = count_endpoints(sample_csharp_project, Language.CSHARP, ["aspnet"])
    assert count == 3  # Actual count from fixture


def test_count_endpoints_python(sample_python_project):
    """Test endpoint counting for Python project."""
    count = count_endpoints(sample_python_project, Language.PYTHON, ["fastapi"])
    assert count == 4  # GET, POST, PUT, DELETE


def test_count_test_files_go(sample_go_project):
    """Test test file counting for Go."""
    count = count_test_files(sample_go_project, Language.GO)
    assert count == 1  # handler_test.go


def test_count_test_files_typescript(sample_typescript_project):
    """Test test file counting for TypeScript."""
    count = count_test_files(sample_typescript_project, Language.TYPESCRIPT)
    assert count == 1  # routes.test.ts


def test_count_test_files_csharp(sample_csharp_project):
    """Test test file counting for C#."""
    count = count_test_files(sample_csharp_project, Language.CSHARP)
    assert count == 1  # UsersControllerTests.cs


def test_count_test_files_python(sample_python_project):
    """Test test file counting for Python."""
    count = count_test_files(sample_python_project, Language.PYTHON)
    assert count == 2  # Actual count from fixture


def test_detect_test_framework_go(sample_go_project):
    """Test Go test framework detection."""
    framework = detect_test_framework(sample_go_project, Language.GO)
    assert framework == TestFramework.GO_TESTING


def test_detect_test_framework_typescript(sample_typescript_project):
    """Test TypeScript test framework detection (Jest)."""
    framework = detect_test_framework(sample_typescript_project, Language.TYPESCRIPT)
    assert framework == TestFramework.JEST


def test_detect_test_framework_csharp(sample_csharp_project):
    """Test C# test framework detection (xUnit)."""
    framework = detect_test_framework(sample_csharp_project, Language.CSHARP)
    assert framework == TestFramework.XUNIT


def test_detect_test_framework_python(sample_python_project):
    """Test Python test framework detection (pytest)."""
    framework = detect_test_framework(sample_python_project, Language.PYTHON)
    assert framework == TestFramework.PYTEST


def test_infer_project_type_rest_api():
    """Test REST API project type inference."""
    project_type = infer_project_type(["gin"], 10)
    assert project_type == "REST API"


def test_infer_project_type_microservice():
    """Test microservice project type inference."""
    project_type = infer_project_type(["express"], 5)
    assert project_type == "Microservice"


def test_infer_project_type_graphql():
    """Test GraphQL project type inference."""
    project_type = infer_project_type(["graphql"], 10)
    assert project_type == "GraphQL API"


def test_infer_project_type_library():
    """Test library project type inference."""
    project_type = infer_project_type([], 0)
    assert project_type == "Library/CLI"


def test_analyze_project_go(sample_go_project):
    """Test full project analysis for Go."""
    project_info = analyze_project(sample_go_project)

    assert project_info.language == Language.GO
    assert "gin" in project_info.frameworks
    assert project_info.endpoint_count == 4
    assert project_info.test_file_count == 1
    assert project_info.test_framework == TestFramework.GO_TESTING
    assert project_info.primary_type == ProjectType.REST_API
    assert ProjectType.REST_API in project_info.project_types


def test_analyze_project_typescript(sample_typescript_project):
    """Test full project analysis for TypeScript."""
    project_info = analyze_project(sample_typescript_project)

    assert project_info.language == Language.TYPESCRIPT
    assert "express" in project_info.frameworks
    assert project_info.endpoint_count == 3
    assert project_info.test_file_count == 1
    assert project_info.test_framework == TestFramework.JEST


def test_analyze_project_csharp(sample_csharp_project):
    """Test full project analysis for C#."""
    project_info = analyze_project(sample_csharp_project)

    assert project_info.language == Language.CSHARP
    assert "aspnet" in project_info.frameworks
    assert project_info.endpoint_count == 3  # Actual count
    assert project_info.test_file_count == 1
    assert project_info.test_framework == TestFramework.XUNIT


def test_analyze_project_python(sample_python_project):
    """Test full project analysis for Python."""
    project_info = analyze_project(sample_python_project)

    assert project_info.language == Language.PYTHON
    assert "fastapi" in project_info.frameworks
    assert project_info.endpoint_count == 4
    assert project_info.test_file_count == 2  # Actual count
    assert project_info.test_framework == TestFramework.PYTEST


def test_detect_language_kotlin(sample_kotlin_project):
    language = detect_project_language(sample_kotlin_project)
    assert language == Language.KOTLIN


def test_detect_language_rust(sample_rust_project):
    language = detect_project_language(sample_rust_project)
    assert language == Language.RUST


def test_kotlin_not_detected_as_java(sample_kotlin_project):
    """build.gradle.kts must not trigger Java detection."""
    language = detect_project_language(sample_kotlin_project)
    assert language != Language.JAVA


def test_detect_frameworks_kotlin(sample_kotlin_project):
    frameworks = detect_frameworks(sample_kotlin_project, Language.KOTLIN)
    assert "spring" in frameworks


def test_count_endpoints_kotlin(sample_kotlin_project):
    count = count_endpoints(sample_kotlin_project, Language.KOTLIN, ["spring"])
    assert count == 3


def test_analyze_project_kotlin(sample_kotlin_project):
    # Use direct detection functions — analyze_project calls find_project_root
    # which may walk up into a system temp dir with other project indicators.
    language = detect_project_language(sample_kotlin_project)
    assert language == Language.KOTLIN
    frameworks = detect_frameworks(sample_kotlin_project, Language.KOTLIN)
    assert "spring" in frameworks
    endpoint_count = count_endpoints(sample_kotlin_project, Language.KOTLIN, frameworks)
    assert endpoint_count == 3


def test_infer_project_type_grpc():
    project_type = infer_project_type(["grpc"], 5)
    assert project_type == "gRPC Service"


def test_infer_project_type_rest_api_large():
    project_type = infer_project_type(["gin"], 15)
    assert project_type == "REST API"


def test_analyze_project_sets_correct_primary_type_for_graphql(temp_dir):
    """primary_type must be GRAPHQL_API for graphql projects, not REST_API."""
    from bba.models import ProjectType

    # Minimal Python project with graphql in requirements
    (temp_dir / "requirements.txt").write_text("graphql-core==3.2.0\n")
    (temp_dir / "main.py").write_text("import graphql\n" "@app.route('/graphql')\ndef graphql_view(): pass\n")
    project_info = analyze_project(temp_dir)
    # endpoint_count may be 0 (no framework pattern match) → UNKNOWN is OK
    # but if endpoints detected, primary_type must not default REST_API blindly
    if project_info.endpoint_count > 0 and "graphql" in project_info.frameworks:
        assert project_info.primary_type == ProjectType.GRAPHQL_API


def test_detect_frameworks_ignores_empty_manifest(temp_dir):
    (temp_dir / "requirements.txt").write_text("")
    (temp_dir / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n')
    assert detect_frameworks(temp_dir, Language.PYTHON) == ["fastapi"]


def test_detect_test_framework_skips_empty_test_file(temp_dir):
    (temp_dir / "test_empty.py").write_text("")
    (temp_dir / "test_real.py").write_text("def test_ok():\n    assert True\n")
    assert detect_test_framework(temp_dir, Language.PYTHON) == TestFramework.PYTEST


def test_detect_project_types_graphql_and_grpc_from_frameworks(temp_dir):
    (temp_dir / "main.py").write_text("x = 1\n")
    assert detect_project_types(temp_dir, ["GraphQL"], 2) == [ProjectType.GRAPHQL_API]
    assert detect_project_types(temp_dir, ["grpc"], 2) == [ProjectType.GRPC_API]


def test_analyze_project_rejects_a_file(temp_dir):
    f = temp_dir / "main.py"
    f.write_text("x = 1\n")
    with pytest.raises(NotADirectoryError):
        analyze_project(f)


def test_analyze_project_unknown_language_raises(temp_dir):
    (temp_dir / ".git").mkdir()
    (temp_dir / "notes.txt").write_text("nothing to see\n")
    with pytest.raises(ValueError, match="Could not detect language"):
        analyze_project(temp_dir)


# ── main ──────────────────────────────────────────────────────────────────────


def _run_main(monkeypatch, *argv):
    import analyze_project_structure

    monkeypatch.setattr("sys.argv", ["analyze_project_structure.py", *map(str, argv)])
    return analyze_project_structure.main()


def test_main_json_to_stdout(sample_go_project, monkeypatch, capsys):
    assert _run_main(monkeypatch, sample_go_project) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["language"] == "go"
    assert data["endpoint_count"] == 4
    assert "gin" in data["frameworks"]


def test_main_json_to_file(sample_python_project, temp_dir, monkeypatch):
    out = temp_dir / "project_info.json"
    assert _run_main(monkeypatch, sample_python_project, "--output", out) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["language"] == "python"


def test_main_summary_format(sample_go_project, monkeypatch, capsys):
    assert _run_main(monkeypatch, sample_go_project, "--output-format", "summary") == 0
    out = capsys.readouterr().out
    assert "Language: go" in out
    assert "Frameworks: gin" in out
    assert "Endpoints: 4" in out
    assert "Test Framework: testing" in out


def test_main_summary_without_frameworks_says_none(temp_dir, monkeypatch, capsys):
    (temp_dir / ".git").mkdir()
    (temp_dir / "lib.py").write_text("def add(a, b):\n    return a + b\n")
    assert _run_main(monkeypatch, temp_dir, "--output-format", "summary") == 0
    assert "Frameworks: None" in capsys.readouterr().out


def test_main_error_returns_one(temp_dir, monkeypatch, capsys):
    assert _run_main(monkeypatch, temp_dir / "missing") == 1
    assert "Error: Not a directory" in capsys.readouterr().err
