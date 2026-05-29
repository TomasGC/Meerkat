#!/usr/bin/env python3
"""Tests for detect_project_type.py"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from cli.detect_project_type import detect_project_type
from common.utils import write_file_safe

def test_detect_cypress_project(tmp_path):
    """Test detecting Cypress project."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "devDependencies": {
            "cypress": "^12.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "cypress"
    assert result["technology"] == "Cypress E2E Testing"
    assert result["build"] == "npm install"
    assert result["test"] == "npx cypress run"

def test_detect_vuejs_project_with_vue_dependency(tmp_path):
    """Test detecting Vue.js project with vue dependency."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {
            "vue": "^3.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "vuejs"
    assert result["technology"] == "Vue.js 3"
    assert result["build"] == "npm run build"
    assert result["test"] == "npm run test:unit"

def test_detect_vuejs_project_with_vite_config(tmp_path):
    """Test detecting Vue.js project with vite.config.js."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({"name": "test-project"}))

    vite_config = tmp_path / "vite.config.js"
    write_file_safe(vite_config, "export default {}")

    result = detect_project_type(tmp_path)

    assert result["type"] == "vuejs"

def test_detect_react_project(tmp_path):
    """Test detecting React project."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {
            "react": "^18.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "node"
    assert result["technology"] == "React"
    assert result["build"] == "npm run build"
    assert result["test"] == "npm test"

def test_detect_nodejs_project(tmp_path):
    """Test detecting generic Node.js project."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {}
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "node"
    assert result["technology"] == "Node.js"
    assert result["build"] == "npm install"
    assert result["test"] == "npm test"

def test_detect_go_project(tmp_path):
    """Test detecting Go project."""
    go_mod = tmp_path / "go.mod"
    write_file_safe(go_mod, "module example.com/myproject\n\ngo 1.21")

    result = detect_project_type(tmp_path)

    assert result["type"] == "go"
    assert result["technology"] == "Go"
    assert result["build"] == "go build"
    assert result["test"] == "go test ./..."

def test_detect_dotnet_project(tmp_path):
    """Test detecting .NET project."""
    csproj = tmp_path / "MyProject.csproj"
    write_file_safe(csproj, "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>")

    result = detect_project_type(tmp_path)

    assert result["type"] == "dotnet"
    assert result["technology"] == ".NET"
    assert result["build"] == "dotnet build"
    assert result["test"] == "dotnet test"

def test_detect_aspnet_mvc_project(tmp_path):
    """Test detecting ASP.NET MVC project with cshtml."""
    csproj = tmp_path / "MyProject.csproj"
    write_file_safe(csproj, "<Project Sdk=\"Microsoft.NET.Sdk.Web\"></Project>")

    # Create a cshtml file
    views_dir = tmp_path / "Views" / "Home"
    views_dir.mkdir(parents=True)
    index_cshtml = views_dir / "Index.cshtml"
    write_file_safe(index_cshtml, "@{ ViewData[\"Title\"] = \"Home\"; }")

    result = detect_project_type(tmp_path)

    assert result["type"] == "cshtml"
    assert result["technology"] == "ASP.NET MVC"
    assert result["build"] == "dotnet build"
    assert result["test"] == "dotnet test"

def test_detect_python_project_requirements(tmp_path):
    """Test detecting Python project with requirements.txt."""
    requirements = tmp_path / "requirements.txt"
    write_file_safe(requirements, "pytest\nrequests")

    result = detect_project_type(tmp_path)

    assert result["type"] == "python"
    assert result["technology"] == "Python"
    assert result["build"] == "pip install -r requirements.txt"
    assert result["test"] == "pytest"

def test_detect_python_project_setup_py(tmp_path):
    """Test detecting Python project with setup.py."""
    setup_py = tmp_path / "setup.py"
    write_file_safe(setup_py, "from setuptools import setup\nsetup(name='test')")

    result = detect_project_type(tmp_path)

    assert result["type"] == "python"

def test_detect_python_project_pyproject_toml(tmp_path):
    """Test detecting Python project with pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    write_file_safe(pyproject, "[tool.poetry]\nname = \"test\"")

    result = detect_project_type(tmp_path)

    assert result["type"] == "python"

def test_detect_rust_project(tmp_path):
    """Test detecting Rust project."""
    cargo_toml = tmp_path / "Cargo.toml"
    write_file_safe(cargo_toml, "[package]\nname = \"test\"")

    result = detect_project_type(tmp_path)

    assert result["type"] == "rust"
    assert result["technology"] == "Rust"
    assert result["build"] == "cargo build"
    assert result["test"] == "cargo test"

def test_detect_unknown_project(tmp_path):
    """Test detecting unknown project type."""
    result = detect_project_type(tmp_path)

    assert result["type"] == "unknown"
    assert result["technology"] == "Unknown"
    assert result["build"] == "(To be configured)"
    assert result["test"] == "(To be configured)"

def test_detect_priority_cypress_over_node(tmp_path):
    """Test that Cypress is detected with higher priority than generic Node."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {
            "express": "^4.0.0"
        },
        "devDependencies": {
            "cypress": "^12.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "cypress"

def test_detect_priority_vue_over_node(tmp_path):
    """Test that Vue is detected with higher priority than generic Node."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {
            "vue": "^3.0.0",
            "axios": "^1.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "vuejs"

def test_detect_invalid_package_json_fallback(tmp_path):
    """Test fallback when package.json is invalid."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, "{ invalid json")

    result = detect_project_type(tmp_path)

    # Should fallback to generic Node
    assert result["type"] == "node"
    assert result["technology"] == "Node.js"

def test_detect_dotnet_solution_file(tmp_path):
    """Test detecting .NET project with .sln file."""
    sln = tmp_path / "MySolution.sln"
    write_file_safe(sln, "Microsoft Visual Studio Solution File")

    result = detect_project_type(tmp_path)

    assert result["type"] == "dotnet"

def test_detect_cypress_in_dependencies(tmp_path):
    """Test detecting Cypress in dependencies (not just devDependencies)."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({
        "name": "test-project",
        "dependencies": {
            "cypress": "^12.0.0"
        }
    }))

    result = detect_project_type(tmp_path)

    assert result["type"] == "cypress"

def test_detect_vuejs_with_vite_ts_config(tmp_path):
    """Test detecting Vue with vite.config.ts."""
    package_json = tmp_path / "package.json"
    write_file_safe(package_json, json.dumps({"name": "test-project"}))

    vite_config = tmp_path / "vite.config.ts"
    write_file_safe(vite_config, "export default {}")

    result = detect_project_type(tmp_path)

    assert result["type"] == "vuejs"
