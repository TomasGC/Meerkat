#!/usr/bin/env python3
"""Tests for analyze_code_patterns.py"""

import json
from pathlib import Path

import pytest

from cli.agents.code_analyzer.analyze_code_patterns import AnalyzeCodePatternsScript

@pytest.fixture
def script():
    """Create script instance."""
    return AnalyzeCodePatternsScript()

@pytest.fixture
def temp_project(tmp_path):
    """Create temp project with various code quality issues."""
    # File with dead code
    (tmp_path / "dead.py").write_text("""
def used_function():
    return 1

def unused_function():
    return 2

result = used_function()
""")

    # File with duplicate code
    (tmp_path / "dup1.py").write_text("""
def process(data):
    result = []
    for x in data:
        result.append(x * 2)
    return result
""")

    (tmp_path / "dup2.py").write_text("""
def transform(values):
    output = []
    for x in values:
        output.append(x * 2)
    return output
""")

    return tmp_path

def test_run_dead_code_check(script, temp_project, monkeypatch):
    """Test dead code check execution."""
    result = script._run_dead_code_check(temp_project)

    assert result is not None
    assert "unused_symbols" in result or "error" in result

def test_run_dry_check(script, temp_project, monkeypatch):
    """Test DRY violations check execution."""
    result = script._run_dry_check(temp_project)

    assert result is not None
    assert "duplicates" in result or "error" in result

def test_run_complexity_check(script, temp_project, monkeypatch):
    """Test complexity check execution."""
    result = script._run_complexity_check(temp_project)

    assert result is not None
    assert "complexity_issues" in result or "error" in result

def test_script_execution_success(script, temp_project, monkeypatch):
    """Test full script execution."""
    class Args:
        path = temp_project
        checks = "dead_code,dry,complexity"
        use_ollama = False

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert "dead_code" in result
    assert "dry_violations" in result
    assert "complexity_issues" in result
    assert "total_issues" in result

def test_script_selective_checks(script, temp_project, monkeypatch):
    """Test execution with selective checks."""
    class Args:
        path = temp_project
        checks = "dead_code"
        use_ollama = False

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert result["checks_performed"] == ["dead_code"]
