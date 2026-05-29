#!/usr/bin/env python3
"""Tests for calculate_complexity.py"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cli.agents.code_analyzer.calculate_complexity import CalculateComplexityScript


@pytest.fixture
def script():
    """Create script instance."""
    return CalculateComplexityScript()


@pytest.fixture
def temp_complex_file(tmp_path):
    """Create temp file with complex code."""
    file = tmp_path / "complex.py"
    file.write_text("""
def simple_function():
    return 1

def complex_function(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                if item < 100:
                    result.append(item)
                else:
                    result.append(item // 2)
            elif item % 3 == 0:
                result.append(item * 2)
        else:
            result.append(0)
    return result
""")
    return file


def test_calculate_cyclomatic_simple(script):
    """Test cyclomatic complexity for simple function."""
    code = "def foo(): return 1"
    tree = ast.parse(code)
    func = tree.body[0]

    complexity = script._calculate_cyclomatic(func)
    assert complexity == 1  # Base complexity


def test_calculate_cyclomatic_with_conditions(script):
    """Test cyclomatic complexity with if statements."""
    code = """
def foo(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
"""
    tree = ast.parse(code)
    func = tree.body[0]

    complexity = script._calculate_cyclomatic(func)
    assert complexity >= 2  # At least 2 decision points


def test_calculate_nesting_depth(script):
    """Test nesting depth calculation."""
    code = """
def foo():
    if True:
        if True:
            if True:
                pass
"""
    tree = ast.parse(code)
    func = tree.body[0]

    depth = script._calculate_nesting(func)
    assert depth == 3


def test_calculate_severity_high(script):
    """Test high severity calculation."""
    severity = script._calculate_severity(15, 5, 100)
    assert severity == "high"


def test_script_execution_success(script, temp_complex_file, monkeypatch):
    """Test full script execution."""
    class Args:
        path = temp_complex_file.parent
        threshold = 5

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert result["files_analyzed"] == 1
    assert "complexity_issues" in result
