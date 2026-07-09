#!/usr/bin/env python3
"""Tests for find_unused_code.py"""

from pathlib import Path

import pytest

from cli.agents.code_analyzer.find_unused_code import FindUnusedCodeScript

@pytest.fixture
def script():
    """Create script instance."""
    return FindUnusedCodeScript()

@pytest.fixture
def temp_python_file(tmp_path):
    """Create temp Python file with unused code."""
    file = tmp_path / "test.py"
    file.write_text("""
def used_function():
    return "used"

def unused_function():
    return "unused"

class UsedClass:
    pass

class UnusedClass:
    pass

# Call used_function and UsedClass
result = used_function()
obj = UsedClass()
""")
    return file

def test_detect_language_python(script, tmp_path):
    """Test Python language detection."""
    (tmp_path / "test.py").touch()
    lang = script._detect_language(tmp_path)
    assert lang == "python"

def test_detect_language_typescript(script, tmp_path):
    """Test TypeScript language detection."""
    (tmp_path / "test.ts").touch()
    lang = script._detect_language(tmp_path)
    assert lang == "typescript"

def test_find_unused_python_functions(script, temp_python_file):
    """Test detection of unused Python functions."""
    unused = script._find_unused_python(temp_python_file, recursive=False)

    unused_names = {u.name for u in unused}
    assert "unused_function" in unused_names
    assert "UnusedClass" in unused_names
    assert "used_function" not in unused_names
    assert "UsedClass" not in unused_names

def test_unused_symbol_confidence(script, temp_python_file):
    """Test confidence levels for unused symbols."""
    unused = script._find_unused_python(temp_python_file, recursive=False)

    # All should be high confidence (not exported)
    for u in unused:
        assert u.confidence == "high"

def test_script_execution_success(script, temp_python_file, monkeypatch):
    """Test full script execution."""
    class Args:
        path = temp_python_file.parent
        recursive = False
        language = "python"

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert result["language"] == "python"
    assert result["total_unused"] >= 1
    assert len(result["unused_symbols"]) >= 1
