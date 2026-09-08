#!/usr/bin/env python3
"""Tests for generate_ci_workflow.py — unit tests"""

from pathlib import Path

from generate_ci_workflow import (
    _COLLECT_CMD,
    _SETUP_STEPS,
    _detect_reportgenerator_install,
    generate_makefile_target,
    generate_npm_scripts,
    generate_workflow,
)
from common.models import Language, TestFramework

def test_generate_workflow_python_has_pytest_setup():
    wf = generate_workflow(Language.PYTHON, [], TestFramework.PYTEST)
    assert "setup-python" in wf
    assert "pytest" in wf

def test_generate_workflow_go_has_go_setup():
    wf = generate_workflow(Language.GO, [], TestFramework.GO_TESTING)
    assert "setup-go" in wf

def test_generate_workflow_kotlin_has_java_setup():
    wf = generate_workflow(Language.KOTLIN, [], TestFramework.JUNIT)
    assert "setup-java" in wf
    assert "temurin" in wf

def test_generate_workflow_rust_has_rust_toolchain():
    wf = generate_workflow(Language.RUST, [], TestFramework.UNKNOWN)
    assert "rust-toolchain" in wf
    assert "cargo-tarpaulin" in wf

def test_generate_workflow_swift_has_swift_setup():
    wf = generate_workflow(Language.SWIFT, [], TestFramework.UNKNOWN)
    assert "setup-swift" in wf

def test_generate_workflow_csharp_has_dotnet_setup():
    wf = generate_workflow(Language.CSHARP, [], TestFramework.XUNIT)
    assert "setup-dotnet" in wf
    assert "reportgenerator" in wf

def test_generate_workflow_unknown_language_does_not_crash():
    wf = generate_workflow(Language.UNKNOWN, [], TestFramework.UNKNOWN)
    assert "jobs:" in wf
    assert "strategy:" in wf

def test_generate_workflow_has_matrix_with_four_tiers():
    wf = generate_workflow(Language.PYTHON, [], TestFramework.PYTEST)
    assert "unit" in wf
    assert "int_mock" in wf
    assert "int_real" in wf
    assert "e2e" in wf

def test_generate_workflow_has_codecov_action():
    wf = generate_workflow(Language.PYTHON, [], TestFramework.PYTEST)
    assert "codecov/codecov-action" in wf

def test_generate_workflow_has_combine_job():
    wf = generate_workflow(Language.PYTHON, [], TestFramework.PYTEST)
    assert "coverage-combined" in wf

def test_generate_workflow_has_artifact_upload():
    wf = generate_workflow(Language.PYTHON, [], TestFramework.PYTEST)
    assert "upload-artifact" in wf

def test_generate_workflow_project_name_in_title():
    wf = generate_workflow(Language.GO, [], TestFramework.GO_TESTING, project_name="my-service")
    assert "my-service" in wf

def test_collect_cmd_contains_swift():
    assert Language.SWIFT in _COLLECT_CMD

def test_collect_cmd_contains_kotlin():
    assert Language.KOTLIN in _COLLECT_CMD

def test_collect_cmd_contains_rust():
    assert Language.RUST in _COLLECT_CMD

def test_collect_cmd_all_setup_languages_have_collect_cmd():
    for lang in _SETUP_STEPS:
        assert lang in _COLLECT_CMD, f"{lang} in _SETUP_STEPS but missing from _COLLECT_CMD"

def test_detect_reportgenerator_install_csharp_empty():
    assert _detect_reportgenerator_install(Language.CSHARP) == ""

def test_detect_reportgenerator_install_non_csharp():
    cmd = _detect_reportgenerator_install(Language.PYTHON)
    assert "reportgenerator" in cmd
    assert "dotnet tool install" in cmd

def test_generate_makefile_target_python_has_pytest():
    mk = generate_makefile_target(Language.PYTHON)
    assert "pytest" in mk
    assert ".PHONY:" in mk
    assert "coverage:" in mk

def test_generate_makefile_target_go_has_go_test():
    mk = generate_makefile_target(Language.GO)
    assert "go test" in mk

def test_generate_makefile_target_unknown_has_fallback():
    mk = generate_makefile_target(Language.UNKNOWN)
    assert "collect_runtime_coverage.py" in mk

def test_generate_npm_scripts_typescript():
    s = generate_npm_scripts(Language.TYPESCRIPT)
    assert '"coverage:unit"' in s
    assert "jest" in s

def test_generate_npm_scripts_javascript():
    s = generate_npm_scripts(Language.JAVASCRIPT)
    assert '"coverage:unit"' in s

def test_generate_npm_scripts_non_js_empty():
    assert generate_npm_scripts(Language.PYTHON) == ""
    assert generate_npm_scripts(Language.GO) == ""
    assert generate_npm_scripts(Language.RUST) == ""

def test_swift_local_cmd_present():
    from generate_ci_workflow import _LOCAL_CMD
    assert Language.SWIFT in _LOCAL_CMD
    assert "xcodebuild" in _LOCAL_CMD[Language.SWIFT]

def test_makefile_target_swift_has_xcodebuild():
    target = generate_makefile_target(Language.SWIFT)
    assert "xcodebuild" in target
