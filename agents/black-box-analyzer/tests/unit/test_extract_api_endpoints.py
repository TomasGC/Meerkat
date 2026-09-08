#!/usr/bin/env python3
"""Tests for extract_api_endpoints.py"""

from pathlib import Path

# Add scripts directory to path

from common.models import HTTPMethod, Language
from extract_api_endpoints import (
    extract_csharp_endpoints,
    extract_endpoints,
    extract_go_endpoints,
    extract_params_from_path,
    extract_python_endpoints,
    extract_typescript_endpoints,
)

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
