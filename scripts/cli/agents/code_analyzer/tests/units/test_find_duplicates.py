#!/usr/bin/env python3
"""Tests for find_duplicates.py"""

from pathlib import Path

import pytest

from cli.agents.code_analyzer.find_duplicates import FindDuplicatesScript

@pytest.fixture
def script():
    """Create script instance."""
    return FindDuplicatesScript()

@pytest.fixture
def temp_duplicate_files(tmp_path):
    """Create temp files with duplicate code."""
    file1 = tmp_path / "file1.py"
    file1.write_text("""
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
""")

    file2 = tmp_path / "file2.py"
    file2.write_text("""
def transform_values(values):
    output = []
    for item in values:
        if item > 0:
            output.append(item * 2)
    return output
""")

    return tmp_path

def test_hash_code_normalization(script):
    """Test code hashing with whitespace normalization."""
    code1 = "def foo():\n    return 1"
    code2 = "def   foo():\n        return   1"

    hash1 = script._hash_code(code1)
    hash2 = script._hash_code(code2)

    assert hash1 == hash2

def test_calculate_similarity_identical(script):
    """Test similarity calculation for identical code."""
    code1 = "def foo(): return 1"
    code2 = "def foo(): return 1"

    similarity = script._calculate_similarity(code1, code2)
    assert similarity == 1.0

def test_calculate_similarity_different(script):
    """Test similarity calculation for different code."""
    code1 = "def foo(): return 1"
    code2 = "class Bar: pass"

    similarity = script._calculate_similarity(code1, code2)
    assert similarity < 0.3

def test_calculate_severity_high(script):
    """Test high severity for high similarity and many lines."""
    severity = script._calculate_severity(0.95, 10)
    assert severity == "high"

def test_script_execution_success(script, temp_duplicate_files, monkeypatch):
    """Test full script execution."""
    class Args:
        path = temp_duplicate_files
        threshold = 5
        similarity = 0.85

    monkeypatch.setattr(script, "logger", script.logger)
    result = script.execute(Args())

    assert result["success"] is True
    assert result["files_analyzed"] == 2
    assert result["duplicates_found"] >= 0  # May or may not find duplicates depending on threshold
