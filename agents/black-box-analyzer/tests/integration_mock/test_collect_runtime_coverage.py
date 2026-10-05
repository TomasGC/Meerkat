#!/usr/bin/env python3
"""Tests for collect_runtime_coverage.py — int_mock tests (subprocess/tool patched)"""

from pathlib import Path
from unittest.mock import patch

from collect_runtime_coverage import (
    _convert_go_cover_to_lcov,
    _run,
    _which,
    collect_coverage,
    collect_dotnet,
    collect_go,
    collect_java,
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

    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=capturing_run
    ):
        collect_python(sample_python_project, temp_dir, ("unit",), dry_run=True)

    assert len(captured_cmds) == 1
    assert captured_cmds[0][0] == _sys.executable


def test_collect_coverage_creates_output_dir(sample_python_project, temp_dir):
    output_dir = temp_dir / "new-cov-dir"
    assert not output_dir.exists()
    with patch("collect_runtime_coverage._which", return_value=False):
        collect_coverage(sample_python_project, output_dir, ("unit",), dry_run=False)
    assert output_dir.exists()


# ── Real-run branches: the tool is mocked, the files it would write are real ──


def _which_only(*available):
    """Patch target for _which: only the named tools are installed."""
    return lambda name: name in available


def _writing_run(target_for_cmd):
    """Fake _run that writes the file the real tool would produce, then succeeds."""

    def fake_run(cmd, cwd, dry_run):
        target = target_for_cmd(cmd)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SF:src/a.py\nDA:1,1\nend_of_record\n")
        return 0

    return fake_run


def _recording_run(cmds):
    def fake_run(cmd, cwd, dry_run):
        cmds.append(cmd)
        return 0

    return fake_run


def _go_profile_writer(cmd, cwd, dry_run):
    profile = next(arg for arg in cmd if arg.startswith("-coverprofile="))
    Path(profile.split("=", 1)[1]).write_text("mode: atomic\npkg/a.go:4.1,6.2 1 2\n")
    return 0


def test_run_dry_run_skips_subprocess(temp_dir, capsys):
    with patch("collect_runtime_coverage.subprocess.run") as run:
        assert _run(["echo", "hi"], temp_dir, dry_run=True) == 0
    run.assert_not_called()
    assert "$ echo hi" in capsys.readouterr().err


def test_run_returns_subprocess_returncode(temp_dir):
    with patch("collect_runtime_coverage.subprocess.run") as run:
        run.return_value.returncode = 3
        assert _run(["tool"], temp_dir, dry_run=False) == 3
    assert run.call_args.kwargs["cwd"] == str(temp_dir)


def test_which_reflects_shutil_which():
    with patch("collect_runtime_coverage.shutil.which", return_value=None):
        assert _which("nope") is False
    with patch("collect_runtime_coverage.shutil.which", return_value="/usr/bin/go"):
        assert _which("go") is True


def test_convert_go_cover_skips_malformed_lines(temp_dir):
    cov = temp_dir / "bad.out"
    cov.write_text("mode: atomic\nno-colon-here\npkg/a.go:x.1,2.1 1 zz\npkg/a.go:7.1,8.1 1 4\n")
    out = temp_dir / "out.lcov"
    _convert_go_cover_to_lcov(cov, out)
    assert out.read_text() == "SF:pkg/a.go\nDA:7,4\nend_of_record"


def test_collect_python_failed_tier_without_lcov_is_dropped(sample_python_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=1
    ):
        outputs = collect_python(sample_python_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "pytest tier=unit failed (rc=1)" in capsys.readouterr().err


def test_collect_python_failed_tier_with_lcov_is_kept(sample_python_project, temp_dir):
    (temp_dir / "coverage_unit.lcov").write_text("SF:a\nend_of_record\n")
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=1
    ):
        outputs = collect_python(sample_python_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {"unit": temp_dir / "coverage_unit.lcov"}


def test_collect_js_moves_generated_lcov_into_tier_file(sample_typescript_project, temp_dir):
    out = temp_dir / "cov"
    fake = _writing_run(lambda cmd: out / "unit" / "lcov.info")
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=fake
    ):
        outputs = collect_js(sample_typescript_project, out, ("unit",), dry_run=False)
    assert outputs == {"unit": out / "coverage_unit.lcov"}
    assert (out / "coverage_unit.lcov").read_text().startswith("SF:")
    assert not (out / "unit" / "lcov.info").exists()


def test_collect_js_missing_lcov_warns_and_drops_tier(sample_typescript_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=2
    ):
        outputs = collect_js(sample_typescript_project, temp_dir, ("e2e",), dry_run=False)
    assert outputs == {}
    assert "jest tier=e2e failed (rc=2)" in capsys.readouterr().err


def test_collect_go_without_gcov2lcov_converts_profile_itself(sample_go_project, temp_dir):
    with patch("collect_runtime_coverage._which", side_effect=_which_only("go")), patch(
        "collect_runtime_coverage._run", side_effect=_go_profile_writer
    ):
        outputs = collect_go(sample_go_project, temp_dir, ("int_mock",), dry_run=False)
    lcov = temp_dir / "coverage_int_mock.lcov"
    assert outputs == {"int_mock": lcov}
    assert lcov.read_text() == "SF:pkg/a.go\nDA:4,2\nend_of_record"


def test_collect_go_uses_tier_as_build_tag(sample_go_project, temp_dir):
    cmds = []
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=_recording_run(cmds)
    ):
        collect_go(sample_go_project, temp_dir, ("int_real",), dry_run=True)
    assert "-tags=intreal" in cmds[0]


def test_collect_go_with_gcov2lcov_keeps_tier_on_success(sample_go_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=_go_profile_writer
    ), patch("collect_runtime_coverage.subprocess.run") as run:
        run.return_value.returncode = 0
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {"unit": temp_dir / "coverage_unit.lcov"}
    assert run.call_args.args[0][0] == "gcov2lcov"


def test_collect_go_gcov2lcov_failure_drops_tier(sample_go_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=_go_profile_writer
    ), patch("collect_runtime_coverage.subprocess.run") as run:
        run.return_value.returncode = 5
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "gcov2lcov failed (rc=5) for tier=unit" in capsys.readouterr().err


def test_collect_go_failed_run_without_profile_warns(sample_go_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=1
    ):
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "go test tier=unit failed (rc=1)" in capsys.readouterr().err


def test_collect_go_successful_run_without_profile_warns(sample_go_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=0
    ):
        outputs = collect_go(sample_go_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "rc=0 but no coverage file" in capsys.readouterr().err


def test_collect_dotnet_moves_generated_lcov(sample_csharp_project, temp_dir):
    fake = _writing_run(lambda cmd: temp_dir / "unit" / "guid-1" / "coverage.info.lcov")
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=fake
    ):
        outputs = collect_dotnet(sample_csharp_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {"unit": temp_dir / "coverage_unit.lcov"}
    assert (temp_dir / "coverage_unit.lcov").exists()


def test_collect_dotnet_uses_category_filter_per_tier(sample_csharp_project, temp_dir):
    cmds = []
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=_recording_run(cmds)
    ):
        collect_dotnet(sample_csharp_project, temp_dir, ("int_real",), dry_run=True)
    assert "--filter=Category=IntegrationReal" in cmds[0]


def test_collect_dotnet_no_lcov_after_success_warns(sample_csharp_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=0
    ):
        outputs = collect_dotnet(sample_csharp_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "dotnet tier=unit: no lcov file generated" in capsys.readouterr().err


def test_collect_dotnet_failed_run_warns(sample_csharp_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=1
    ):
        outputs = collect_dotnet(sample_csharp_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "dotnet tier=unit failed (rc=1)" in capsys.readouterr().err


def test_collect_java_without_gradle_returns_empty(sample_kotlin_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=False):
        outputs = collect_java(sample_kotlin_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "gradle not found" in capsys.readouterr().err


def test_collect_java_prefers_project_gradlew(sample_kotlin_project, temp_dir):
    (sample_kotlin_project / "gradlew").write_text("#!/bin/sh\n")
    cmds = []
    with patch("collect_runtime_coverage._which", return_value=False), patch(
        "collect_runtime_coverage._run", side_effect=_recording_run(cmds)
    ):
        outputs = collect_java(sample_kotlin_project, temp_dir, ("int_mock",), dry_run=True)
    assert outputs == {"int_mock": temp_dir / "coverage_int_mock.lcov"}
    assert cmds[0][0] == str(sample_kotlin_project / "gradlew")
    assert "-Ptest.groups=integration" in cmds[0]


def test_collect_java_renames_generated_lcov(sample_kotlin_project, temp_dir):
    fake = _writing_run(lambda cmd: temp_dir / "unit" / "jacoco" / "lcov.info")
    with patch("collect_runtime_coverage._which", side_effect=_which_only("gradle")), patch(
        "collect_runtime_coverage._run", side_effect=fake
    ):
        outputs = collect_java(sample_kotlin_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {"unit": temp_dir / "coverage_unit.lcov"}
    assert (temp_dir / "coverage_unit.lcov").exists()


def test_collect_java_without_lcov_plugin_warns(sample_kotlin_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", side_effect=_which_only("gradle")), patch(
        "collect_runtime_coverage._run", return_value=0
    ):
        outputs = collect_java(sample_kotlin_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "no lcov.info found" in capsys.readouterr().err


def test_collect_rust_without_tarpaulin_returns_empty(sample_rust_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", side_effect=_which_only("cargo")):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "cargo-tarpaulin not installed" in capsys.readouterr().err


def test_collect_rust_moves_generated_lcov_per_tier(sample_rust_project, temp_dir):
    fake = _writing_run(lambda cmd: temp_dir / "lcov.info")
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", side_effect=fake
    ):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit", "e2e"), dry_run=False)
    assert outputs == {"unit": temp_dir / "coverage_unit.lcov", "e2e": temp_dir / "coverage_e2e.lcov"}
    assert not (temp_dir / "lcov.info").exists()


def test_collect_rust_failed_run_warns(sample_rust_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=101
    ):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "cargo tarpaulin tier=unit failed (rc=101)" in capsys.readouterr().err


def test_collect_rust_success_without_lcov_warns(sample_rust_project, temp_dir, capsys):
    with patch("collect_runtime_coverage._which", return_value=True), patch(
        "collect_runtime_coverage._run", return_value=0
    ):
        outputs = collect_rust(sample_rust_project, temp_dir, ("unit",), dry_run=False)
    assert outputs == {}
    assert "rc=0 but lcov.info not found" in capsys.readouterr().err


def test_collect_coverage_routes_to_language_collector(sample_go_project, temp_dir):
    with patch("collect_runtime_coverage._which", return_value=True):
        outputs = collect_coverage(sample_go_project, temp_dir / "cov", ("unit",), dry_run=True)
    assert outputs == {"unit": temp_dir / "cov" / "coverage_unit.lcov"}
