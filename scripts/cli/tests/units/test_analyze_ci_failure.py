#!/usr/bin/env python3
"""Tests for analyze_ci_failure.py"""

from pathlib import Path

import pytest

from cli.analyze_ci_failure import (
    CIAnalysis,
    parse_github_url,
)

def test_parse_github_url_pipeline():
    """Test parsing pipeline URL."""
    url = "https://github.com/TomasGC/otter/actions/runs/24734772369"

    result = parse_github_url(url)

    assert result is not None
    repo, run_id = result
    assert repo == "TomasGC/otter"
    assert run_id == "24734772369"

def test_parse_github_url_invalid():
    """Test parsing invalid URL."""
    url = "https://github.com/owner/repo"

    result = parse_github_url(url)

    # Should be None (no PR checks mocked)
    assert result is None

def test_ci_analysis_total_errors():
    """Test total error count."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=["error1", "error2"],
        compilation_errors=["error3"],
        test_failures=["error4", "error5", "error6"],
        lint_errors=[],
        build_errors=["error7"],
        unknown_errors=[]
    )

    assert analysis.total_errors == 7

def test_ci_analysis_priority_infrastructure():
    """Test priority determination with infrastructure errors."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=["error1"],
        compilation_errors=[],
        test_failures=[],
        lint_errors=[],
        build_errors=[],
        unknown_errors=[]
    )

    assert analysis.priority_category == "infrastructure"

def test_ci_analysis_priority_compilation():
    """Test priority determination with compilation errors."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=["error1"],
        compilation_errors=["error2"],  # Compilation has higher priority
        test_failures=[],
        lint_errors=[],
        build_errors=[],
        unknown_errors=[]
    )

    assert analysis.priority_category == "compilation"

def test_ci_analysis_priority_build():
    """Test priority determination with build errors."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=[],
        compilation_errors=[],
        test_failures=[],
        lint_errors=[],
        build_errors=["error1"],
        unknown_errors=[]
    )

    assert analysis.priority_category == "build"

def test_ci_analysis_priority_test():
    """Test priority determination with test errors."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=[],
        compilation_errors=[],
        test_failures=["error1"],
        lint_errors=[],
        build_errors=[],
        unknown_errors=[]
    )

    assert analysis.priority_category == "test"

def test_ci_analysis_priority_unknown():
    """Test priority determination with unknown errors."""
    analysis = CIAnalysis(
        run_id="12345",
        repo="owner/repo",
        infrastructure_errors=[],
        compilation_errors=[],
        test_failures=[],
        lint_errors=[],
        build_errors=[],
        unknown_errors=["error1"]
    )

    assert analysis.priority_category == "unknown"
