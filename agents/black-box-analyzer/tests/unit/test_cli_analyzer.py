#!/usr/bin/env python3
"""Tests for analyzers/cli_analyzer.py: CLI command/flag extraction and scenario generation."""

from pathlib import Path

from analyzers.cli_analyzer import CLIAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, Parameter, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.GO,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_name(entry_points: list[EntryPoint]) -> dict[str, EntryPoint]:
    return {ep.name: ep for ep in entry_points}


# ── can_analyze ───────────────────────────────────────────────────────────────


def test_can_analyze_accepts_cli_project(tmp_path):
    assert CLIAnalyzer().can_analyze(_info(tmp_path, ProjectType.CLI_APP))


def test_can_analyze_rejects_non_cli_project(tmp_path):
    assert not CLIAnalyzer().can_analyze(_info(tmp_path, ProjectType.REST_API))


# ── Go ────────────────────────────────────────────────────────────────────────


def test_go_cobra_command_carries_its_flags(tmp_path):
    _write(
        tmp_path,
        "cmd/deploy.go",
        "package cmd\n\n"
        'var deployCmd = &cobra.Command{ Use: "deploy" }\n'
        'func init() { deployCmd.Flags().StringVarP(&env, "env", "e", "", "target") }\n',
    )

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    deploy = eps["deploy"]
    assert deploy.type == EntryPointType.CLI_COMMAND
    assert deploy.framework == "cobra"
    assert deploy.line_number == 3
    assert Path(deploy.file_path) == Path("cmd/deploy.go")
    assert [(p.name, p.data_type) for p in deploy.params] == [("env", "string")]


def test_go_flag_package_yields_one_flag_entry_point_per_flag(tmp_path):
    _write(
        tmp_path,
        "main.go",
        'package main\nvar port = flag.Int("port", 80, "")\nvar verbose = flag.Bool("verbose", false, "")\n',
    )

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["--port"].type == EntryPointType.CLI_FLAG
    assert eps["--port"].params[0].data_type == "int"
    assert eps["--verbose"].params[0].data_type == "bool"
    assert eps["--verbose"].line_number == 3


def test_empty_source_files_are_skipped(tmp_path):
    for name in ("a.go", "b.py", "c.ts", "d.cs", "e.java"):
        _write(tmp_path, name, "")

    assert CLIAnalyzer().extract_entry_points(tmp_path) == []


# ── Python ────────────────────────────────────────────────────────────────────


def test_python_click_command_collects_preceding_options(tmp_path):
    _write(
        tmp_path,
        "cli.py",
        "import click\n\n"
        "@click.option('--name')\n"
        "@click.option('-c')\n"
        "@click.command()\n"
        "def greet(name, c):\n    pass\n",
    )

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    greet = eps["greet"]
    assert greet.framework == "click"
    assert greet.metadata == {"language": "python", "type": "command"}
    assert [p.name for p in greet.params] == ["name", "c"]


def test_python_click_group_is_reported_as_group(tmp_path):
    _write(tmp_path, "cli.py", "@click.group\ndef main():\n    pass\n")

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["main"].metadata["type"] == "group"


def test_python_click_decorator_without_def_is_ignored(tmp_path):
    _write(tmp_path, "cli.py", "@click.command()\n" + "x = 1\n" * 200)

    assert CLIAnalyzer().extract_entry_points(tmp_path) == []


def test_python_argparse_arguments_become_flags(tmp_path):
    _write(
        tmp_path,
        "tool.py",
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--output')\np.add_argument(\"-v\")\n",
    )

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["--output"].framework == "argparse"
    assert eps["--output"].line_number == 3
    assert "--v" in eps


# ── TypeScript, C#, Java ──────────────────────────────────────────────────────


def test_commander_commands_are_extracted_from_ts_and_js(tmp_path):
    _write(tmp_path, "src/cli.ts", "program.command('build')\n")
    _write(tmp_path, "src/other.js", 'program.command("serve")\n')

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["build"].framework == "commander"
    assert eps["serve"].type == EntryPointType.CLI_COMMAND


def test_csharp_option_attributes_become_flags(tmp_path):
    _write(tmp_path, "Options.cs", 'class Options {\n  [Option("verbose")] public bool Verbose { get; set; }\n}\n')

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["--verbose"].framework == "commandlineparser"
    assert eps["--verbose"].line_number == 2


def test_java_picocli_command_is_extracted(tmp_path):
    _write(tmp_path, "App.java", '@Command(name = "checksum")\nclass App {}\n')

    eps = _by_name(CLIAnalyzer().extract_entry_points(tmp_path))

    assert eps["checksum"].framework == "picocli"
    assert eps["checksum"].metadata == {"language": "java"}


def test_parse_tests_returns_no_tests(tmp_path):
    assert CLIAnalyzer().parse_tests(tmp_path) == []


# ── generate_scenarios ────────────────────────────────────────────────────────


def _command(params: list[Parameter]) -> EntryPoint:
    return EntryPoint(EntryPointType.CLI_COMMAND, "deploy", params, "cmd.go", 1)


def test_scenarios_for_command_with_required_flag_cover_every_type():
    ep = _command([Parameter("env", "flag", "string", required=True)])

    scenarios = CLIAnalyzer().generate_scenarios([ep])

    assert [s.scenario_type for s in scenarios] == ["happy_path", "error", "edge_case", "security"]
    assert scenarios[0].input_combination == {"flags": ["--env=valid"]}
    assert scenarios[0].expected_output == 0
    assert all(s.expected_output == 1 for s in scenarios[1:])
    assert all(s.method_name == "CLI" for s in scenarios)


def test_scenarios_skip_missing_flag_error_when_no_flag_is_required():
    ep = _command([Parameter("env", "flag", "string", required=False)])

    types = [s.scenario_type for s in CLIAnalyzer().generate_scenarios([ep])]

    assert "error" not in types
    assert types == ["happy_path", "edge_case", "security"]


def test_flag_entry_points_produce_no_scenarios():
    flag = EntryPoint(EntryPointType.CLI_FLAG, "--port", [], "main.go", 1)

    assert CLIAnalyzer().generate_scenarios([flag]) == []


def test_analyze_runs_full_pipeline_on_a_cobra_project(tmp_path):
    _write(tmp_path, "main.go", 'var root = &cobra.Command{ Use: "root" }\n')

    result = CLIAnalyzer().analyze(tmp_path, _info(tmp_path, ProjectType.CLI_APP))

    assert result.project_type == ProjectType.CLI_APP
    assert [ep.name for ep in result.entry_points] == ["root"]
    assert result.coverage_matrix.total_scenarios == 2
    assert result.coverage_matrix.tested_scenarios == 0
    assert len(result.risk_assessment) == 2
    assert result.risk_assessment[0].gap.scenario.scenario_type == "security"
