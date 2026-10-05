#!/usr/bin/env python3
"""Tests for generate_ci_workflow.py — unit tests"""

import json

from bba.models import Language, TestFramework
from generate_ci_workflow import (
    _COLLECT_CMD,
    _SETUP_STEPS,
    _detect_reportgenerator_install,
    generate_makefile_target,
    generate_npm_scripts,
    generate_workflow,
)


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


# ── main ──────────────────────────────────────────────────────────────────────


def _project_info(path, **overrides):
    data = {"language": "python", "frameworks": [], "test_framework": "pytest", "root_path": "/work/my-api"}
    data.update(overrides)
    path.write_text(json.dumps(data))
    return path


def _run_main(monkeypatch, *argv):
    import generate_ci_workflow

    monkeypatch.setattr("sys.argv", ["generate_ci_workflow.py", *map(str, argv)])
    return generate_ci_workflow.main()


def test_main_prints_workflow_and_makefile_without_output(temp_dir, monkeypatch, capsys):
    info = _project_info(temp_dir / "project_info.json")
    assert _run_main(monkeypatch, info) == 0
    out = capsys.readouterr().out
    assert "# === .github/workflows/coverage.yml ===" in out
    assert "setup-python" in out
    assert "my-api" in out
    assert "# === Makefile targets ===" in out
    assert "package.json scripts" not in out


def test_main_prints_npm_scripts_for_typescript(temp_dir, monkeypatch, capsys):
    info = _project_info(temp_dir / "project_info.json", language="typescript", test_framework="jest")
    assert _run_main(monkeypatch, info, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "# === package.json scripts ===" in out
    assert '"coverage:unit"' in out


def test_main_writes_workflow_and_appends_makefile(temp_dir, monkeypatch, capsys):
    info = _project_info(temp_dir / "project_info.json", language="go", test_framework="testing")
    workflow = temp_dir / ".github" / "workflows" / "coverage.yml"
    makefile = temp_dir / "Makefile"
    makefile.write_text("build:\n\tgo build\n")
    rc = _run_main(monkeypatch, info, "--output", workflow, "--makefile", makefile, "--project-name", "svc")
    assert rc == 0
    assert "setup-go" in workflow.read_text(encoding="utf-8")
    assert "svc" in workflow.read_text(encoding="utf-8")
    content = makefile.read_text(encoding="utf-8")
    assert content.startswith("build:\n\tgo build\n\n")
    assert "go test" in content
    err = capsys.readouterr().err
    assert "Workflow written to" in err
    assert "Makefile targets appended to" in err


def test_main_dry_run_does_not_touch_makefile(temp_dir, monkeypatch):
    info = _project_info(temp_dir / "project_info.json")
    makefile = temp_dir / "Makefile"
    makefile.write_text("x:\n")
    assert _run_main(monkeypatch, info, "--makefile", makefile, "--dry-run") == 0
    assert makefile.read_text() == "x:\n"


def test_main_resolves_project_info_from_coverage_tiers_dir(temp_dir, monkeypatch, capsys):
    (temp_dir / ".coverage-tiers").mkdir()
    _project_info(temp_dir / ".coverage-tiers" / "project_info.json", language="rust")
    assert _run_main(monkeypatch, temp_dir) == 0
    assert "rust-toolchain" in capsys.readouterr().out


def test_main_directory_without_project_info_fails(temp_dir, monkeypatch, capsys):
    assert _run_main(monkeypatch, temp_dir) == 1
    assert "No project_info.json found" in capsys.readouterr().err


def test_main_unknown_language_and_framework_fall_back(temp_dir, monkeypatch, capsys):
    info = _project_info(temp_dir / "project_info.json", language="cobol", test_framework="punchcards")
    assert _run_main(monkeypatch, info) == 0
    out = capsys.readouterr().out
    assert "jobs:" in out
    assert "collect_runtime_coverage.py" in out
