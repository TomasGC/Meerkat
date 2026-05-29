#!/usr/bin/env python3
"""Tests for analyze_project_structure.py"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from analyze_project_structure import (
    analyze_project,
    count_endpoints,
    count_test_files,
    detect_frameworks,
    detect_language,
    detect_test_framework,
    infer_project_type,
)
from common.models import Language, ProjectType, TestFramework


def test_detect_language_go(sample_go_project):
    """Test Go language detection."""
    language = detect_language(sample_go_project)
    assert language == Language.GO


def test_detect_language_typescript(sample_typescript_project):
    """Test TypeScript language detection."""
    language = detect_language(sample_typescript_project)
    assert language == Language.TYPESCRIPT


def test_detect_language_csharp(sample_csharp_project):
    """Test C# language detection."""
    language = detect_language(sample_csharp_project)
    assert language == Language.CSHARP


def test_detect_language_python(sample_python_project):
    """Test Python language detection."""
    language = detect_language(sample_python_project)
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
