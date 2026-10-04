#!/usr/bin/env python3
"""Tests for generate_comment.py"""

from pathlib import Path

import pytest

from cli.generate_comment import (
    categorize_file,
    generate_implementation_details,
    generate_summary,
)

def test_categorize_file_testing():
    """Test categorizing test files."""
    assert categorize_file("test_module.py") == "testing"
    assert categorize_file("module.test.ts") == "testing"
    assert categorize_file("module.spec.js") == "testing"
    assert categorize_file("tests/test_file.py") == "testing"
    assert categorize_file("fixtures/data.json") == "testing"

def test_categorize_file_scripts():
    """Test categorizing script files."""
    assert categorize_file("script.ps1") == "scripts"
    assert categorize_file("script.sh") == "scripts"
    assert categorize_file("scripts/utility.bash") == "scripts"

def test_categorize_file_scripts_exclude_tests():
    """Test that test scripts are not categorized as scripts."""
    assert categorize_file("script.Tests.ps1") == "testing"

def test_categorize_file_standards():
    """Test categorizing standards files."""
    assert categorize_file("rules/standards-code-quality.md") == "standards"
    assert categorize_file("standards-security.md") == "standards"
    assert categorize_file("coding-standards/README.md") == "standards"

def test_categorize_file_skills():
    """Test categorizing skills files."""
    assert categorize_file("skills/start-session.md") == "skills"
    assert categorize_file("skills/project-setup/SKILL.md") == "skills"

def test_categorize_file_agents():
    """Test categorizing agents files."""
    assert categorize_file("agents/code-reviewer/AGENT.md") == "agents"
    assert categorize_file("agents/analyzer.md") == "agents"

def test_categorize_file_documentation():
    """Test categorizing documentation files."""
    assert categorize_file("README.md") == "documentation"
    assert categorize_file("docs/guide.md") == "documentation"
    assert categorize_file("documentation/api.md") == "documentation"

def test_categorize_file_documentation_exclude():
    """Test excluding certain markdown files."""
    assert categorize_file("CHANGELOG.md") == "code"
    assert categorize_file("LICENSE.md") == "code"

def test_categorize_file_infrastructure():
    """Test categorizing infrastructure files."""
    assert categorize_file("Dockerfile") == "infrastructure"
    assert categorize_file("docker-compose.yml") == "infrastructure"
    assert categorize_file(".gitlab-ci.yml") == "infrastructure"
    assert categorize_file(".github/workflows/ci.yml") == "infrastructure"
    assert categorize_file("k8s/deployment.yaml") == "infrastructure"
    assert categorize_file("terraform/main.tf") == "infrastructure"

def test_categorize_file_configuration():
    """Test categorizing configuration files."""
    assert categorize_file("config.json") == "configuration"
    assert categorize_file("settings.yaml") == "configuration"
    assert categorize_file("app.toml") == "configuration"
    assert categorize_file("app.config") == "configuration"

def test_categorize_file_configuration_exclude():
    """Test excluding package-lock.json."""
    assert categorize_file("package-lock.json") == "code"

def test_categorize_file_code_fallback():
    """Test fallback to code category."""
    assert categorize_file("src/module.py") == "code"
    assert categorize_file("src/component.tsx") == "code"
    assert categorize_file("main.go") == "code"

def test_generate_summary_testing():
    """Test generating summary with testing."""
    categories = {"testing": 10}
    summary = generate_summary(categories)
    assert "comprehensive test suite" in summary

def test_generate_summary_scripts():
    """Test generating summary with scripts."""
    categories = {"scripts": 5}
    summary = generate_summary(categories)
    assert "utility scripts" in summary

def test_generate_summary_multiple():
    """Test generating summary with multiple categories."""
    categories = {
        "testing": 10,
        "scripts": 5,
        "documentation": 3
    }
    summary = generate_summary(categories)
    assert "test suite" in summary or "scripts" in summary or "documentation" in summary

def test_generate_summary_empty():
    """Test generating summary with no categories."""
    categories = {}
    summary = generate_summary(categories)
    assert summary == "project updates"

def test_generate_implementation_details_testing():
    """Test generating details for testing."""
    categories = {"testing": 10}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Test Suite:" in text
    assert "10 files" in text

def test_generate_implementation_details_scripts():
    """Test generating details for scripts."""
    categories = {"scripts": 5}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Utility Scripts:" in text
    assert "5 files" in text

def test_generate_implementation_details_standards():
    """Test generating details for standards."""
    categories = {"standards": 3}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Coding Standards:" in text
    assert "3 files" in text

def test_generate_implementation_details_skills():
    """Test generating details for skills."""
    categories = {"skills": 4}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Custom Skills:" in text
    assert "4 files" in text

def test_generate_implementation_details_infrastructure():
    """Test generating details for infrastructure."""
    categories = {"infrastructure": 2}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Infrastructure:" in text
    assert "2 files" in text

def test_generate_implementation_details_documentation():
    """Test generating details for documentation."""
    categories = {"documentation": 6}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Documentation:" in text
    assert "6 files" in text

def test_generate_implementation_details_code():
    """Test generating details for code."""
    categories = {"code": 15}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Code:" in text
    assert "15 files" in text

def test_generate_implementation_details_multiple():
    """Test generating details for multiple categories."""
    categories = {
        "testing": 10,
        "scripts": 5,
        "code": 15
    }
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Code:" in text
    assert "Test Suite:" in text
    assert "Utility Scripts:" in text

def test_generate_implementation_details_empty():
    """Test generating details with no categories."""
    categories = {}
    details = generate_implementation_details(categories)

    assert details == []
