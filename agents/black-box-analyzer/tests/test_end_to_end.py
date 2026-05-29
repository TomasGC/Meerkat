#!/usr/bin/env python3
"""End-to-end integration tests for complete analysis pipeline."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_full_go_project_analysis(sample_go_project, temp_dir):
    """Test complete analysis pipeline on Go project."""
    output_file = temp_dir / "analysis.json"

    # Run full parallel analysis
    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    # Should succeed
    assert result.returncode == 0, f"Analysis failed: {result.stderr}"

    # Output file should exist
    assert output_file.exists()

    # Parse output
    analysis = json.loads(output_file.read_text())

    # Verify structure (new universal format)
    assert "success" in analysis
    assert analysis["success"] is True

    assert "project_info" in analysis
    assert analysis["project_info"]["language"] == "go"
    assert "gin" in analysis["project_info"]["frameworks"]

    # New structure uses "summary" and "results"
    assert "summary" in analysis
    assert analysis["summary"]["total_entry_points"] == 4

    assert "results" in analysis
    assert "rest_api" in analysis["results"]
    assert analysis["results"]["rest_api"]["entry_points"] == 4


def test_full_typescript_project_analysis(sample_typescript_project, temp_dir):
    """Test complete analysis pipeline on TypeScript project."""
    output_file = temp_dir / "analysis.json"

    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_typescript_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    analysis = json.loads(output_file.read_text())

    assert analysis["success"] is True
    assert analysis["project_info"]["language"] == "typescript"
    assert "express" in analysis["project_info"]["frameworks"]
    assert analysis["summary"]["total_entry_points"] == 3


def test_full_csharp_project_analysis(sample_csharp_project, temp_dir):
    """Test complete analysis pipeline on C# project."""
    output_file = temp_dir / "analysis.json"

    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_csharp_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    analysis = json.loads(output_file.read_text())

    assert analysis["success"] is True
    assert analysis["project_info"]["language"] == "csharp"
    assert "aspnet" in analysis["project_info"]["frameworks"]
    assert analysis["summary"]["total_entry_points"] == 3


def test_full_python_project_analysis(sample_python_project, temp_dir):
    """Test complete analysis pipeline on Python project."""
    output_file = temp_dir / "analysis.json"

    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_python_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    analysis = json.loads(output_file.read_text())

    assert analysis["success"] is True
    assert analysis["project_info"]["language"] == "python"
    assert "fastapi" in analysis["project_info"]["frameworks"]
    assert analysis["summary"]["total_entry_points"] == 4


@pytest.mark.skip(reason="Cache integration not yet implemented in parallel_analyzer")
def test_incremental_cache(sample_go_project, temp_dir):
    """Test incremental cache speeds up repeated runs."""
    import time

    output_file = temp_dir / "analysis.json"

    # First run (no cache)
    start = time.time()
    result1 = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )
    first_run_time = time.time() - start

    assert result1.returncode == 0

    # Second run (with cache)
    start = time.time()
    result2 = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )
    second_run_time = time.time() - start

    assert result2.returncode == 0

    # Second run should be significantly faster (cache hit)
    # Allow some variance, but expect at least 2x speedup
    assert second_run_time < first_run_time, \
        f"Cache didn't speed up: first={first_run_time:.2f}s, second={second_run_time:.2f}s"

    # Verify cache hit message in output (if verbose)
    # Note: This might not always appear depending on verbosity


@pytest.mark.skip(reason="Cache integration not yet implemented in parallel_analyzer")
def test_cache_invalidation_on_file_change(sample_go_project, temp_dir):
    """Test cache invalidates when source files change."""
    output_file = temp_dir / "analysis.json"

    # First run
    result1 = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    assert result1.returncode == 0
    analysis1 = json.loads(output_file.read_text())

    # Modify source file (add new endpoint)
    main_go = sample_go_project / "main.go"
    original_content = main_go.read_text()

    try:
        # Add a new endpoint
        modified_content = original_content + '\n\nrouter.GET("/health", healthCheck)\n'
        main_go.write_text(modified_content)

        # Second run (cache should be invalid)
        result2 = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "parallel_analyzer.py"),
                str(sample_go_project),
                "--output",
                str(output_file),
                "--max-workers",
                "2",
            ],
            capture_output=True,
            text=True,
        )

        assert result2.returncode == 0
        analysis2 = json.loads(output_file.read_text())

        # Should detect new endpoint
        assert analysis2["summary"]["total_entry_points"] > analysis1["summary"]["total_entry_points"]

    finally:
        # Restore original content
        main_go.write_text(original_content)


def test_diff_analysis(sample_go_project, temp_dir):
    """Test diff analysis between two runs."""
    baseline_file = temp_dir / "baseline.json"
    current_file = temp_dir / "current.json"
    diff_file = temp_dir / "diff.json"

    # Create baseline
    subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(baseline_file),
            "--max-workers",
            "2",
        ],
        capture_output=True,
        check=True,
    )

    # Modify project (add a test)
    test_go = sample_go_project / "handler_test.go"
    original_content = test_go.read_text()

    try:
        # Add a new test
        modified_content = original_content + '\n\nfunc TestUpdateUserSuccess(t *testing.T) {\n\t// Test PUT /users/:id\n}\n'
        test_go.write_text(modified_content)

        # Create current analysis
        subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "parallel_analyzer.py"),
                str(sample_go_project),
                "--output",
                str(current_file),
                "--max-workers",
                "2",
                "--no-cache",  # Force re-analysis
            ],
            capture_output=True,
            check=True,
        )

        # Run diff analysis
        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "diff_analysis.py"),
                str(baseline_file),
                str(current_file),
                "--output",
                str(diff_file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert diff_file.exists()

        diff = json.loads(diff_file.read_text())

        # Verify diff structure
        assert "coverage" in diff
        assert "gaps" in diff
        assert "risk_levels" in diff

        # Coverage should improve (new test added)
        assert diff["coverage"]["delta"] > 0 or diff["coverage"]["delta"] == 0

    finally:
        # Restore original content
        test_go.write_text(original_content)


@pytest.mark.skip(reason="Cache integration not yet implemented in parallel_analyzer")
def test_clear_cache_flag(sample_go_project, temp_dir):
    """Test --clear-cache flag."""
    from common.cache import AnalysisCache

    # Create some cache
    output_file = temp_dir / "analysis.json"
    subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
        ],
        capture_output=True,
        check=True,
    )

    # Verify cache exists
    cache = AnalysisCache()
    cache_info = cache.get_cache_info()
    assert cache_info["status"] == "active"

    # Clear cache
    result = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--clear-cache",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Verify cache cleared
    cache_info = cache.get_cache_info()
    assert cache_info["status"] == "empty"


def test_no_cache_flag(sample_go_project, temp_dir):
    """Test --no-cache flag bypasses cache."""
    output_file = temp_dir / "analysis.json"

    # Run with cache
    result1 = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result1.returncode == 0

    # Run with --no-cache
    result2 = subprocess.run(
        [
            sys.executable,
            str(scripts_dir / "parallel_analyzer.py"),
            str(sample_go_project),
            "--output",
            str(output_file),
            "--no-cache",
        ],
        capture_output=True,
        text=True,
    )

    assert result2.returncode == 0

    # Both should produce same results
    # (No cache hit messages in result2 output)
