#!/usr/bin/env python3
"""Tests for collect_runtime_coverage.py — int_mock tests (subprocess/tool patched)"""

from pathlib import Path
from unittest.mock import patch

from collect_runtime_coverage import (
    collect_coverage,
    collect_dotnet,
    collect_go,
    collect_js,
    collect_python,
    collect_rust,
)

def test_collect_python_dry_run_returns_paths(sample_python_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_python(sample_python_project, temp_dir, ("unit", "int_mock"), dry_run=True)
    assert "unit" in outputs
    assert "int_mock" in outputs
    assert not outputs["unit"].exists()

def test_collect_go_dry_run_returns_paths(sample_go_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=True)
    assert "unit" in outputs

def test_collect_js_dry_run_returns_paths(sample_typescript_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_js(sample_typescript_project, temp_dir, ("unit",), dry_run=True)
    assert "unit" in outputs

def test_collect_dotnet_dry_run_returns_paths(sample_csharp_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_dotnet(sample_csharp_project, temp_dir, ("unit",), dry_run=True)
    assert "unit" in outputs

def test_collect_rust_dry_run_returns_paths(sample_rust_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit",), dry_run=True)
    assert "unit" in outputs

def test_collect_python_no_pytest_returns_empty(sample_python_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_python(sample_python_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}

def test_collect_go_no_go_returns_empty(sample_go_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}

def test_collect_js_no_jest_returns_empty(sample_typescript_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_js(sample_typescript_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}

def test_collect_rust_no_cargo_returns_empty(sample_rust_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}

def test_collect_dotnet_no_dotnet_returns_empty(sample_csharp_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_dotnet(sample_csharp_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}

def test_collect_js_detects_jest_cmd_on_windows(temp_dir):
    project = temp_dir / "js-win-project"
    project.mkdir()
    bin_dir = project / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    jest_cmd_file = bin_dir / "jest.cmd"
    jest_cmd_file.write_text("@echo off\r\nnode jest.js\r\n")

    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_js(project, temp_dir / "cov", ("unit",), dry_run=True)
    assert "unit" in outputs

def test_collect_python_uses_sys_executable(sample_python_project, temp_dir, capsys):
    import sys as _sys
    captured_cmds = []

    def capturing_run(cmd, cwd, dry_run):
        captured_cmds.append(cmd)
        return 0

    with patch("collect_runtime_coverage._which", return_value=True), \
         patch("collect_runtime_coverage._run", side_effect=capturing_run):
        collect_python(sample_python_project, temp_dir, ("unit",), dry_run=True)

    assert len(captured_cmds) == 1
    assert captured_cmds[0][0] == _sys.executable

def test_collect_coverage_creates_output_dir(sample_python_project, temp_dir):
    output_dir = temp_dir / "new-cov-dir"
    assert not output_dir.exists()
    with patch("collect_runtime_coverage._which", return_value=False):
        collect_coverage(sample_python_project, output_dir, ("unit",), dry_run=False)
    assert output_dir.exists()
