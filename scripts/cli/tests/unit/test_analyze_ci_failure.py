#!/usr/bin/env python3
"""Tests for analyze_ci_failure.py"""

import json
from unittest.mock import patch

import pytest
from cli.analyze_ci_failure import (
    AnalyzeCIFailureScript,
    CIAnalysis,
    analyze_logs,
    fetch_failed_logs,
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
        unknown_errors=[],
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
        unknown_errors=[],
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
        unknown_errors=[],
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
        unknown_errors=[],
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
        unknown_errors=[],
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
        unknown_errors=["error1"],
    )

    assert analysis.priority_category == "unknown"


# ── parse_github_url: PR URL ──────────────────────────────────────────────────


def test_parse_github_url_pr_resolves_latest_workflow_run():
    """A PR URL is resolved to its first workflow run through `gh pr view`."""
    with patch("cli.analyze_ci_failure.run_command", return_value=(0, '[{"workflowRunId":987}]', "")) as run:
        assert parse_github_url("https://github.com/owner/repo/pull/42") == ("owner/repo", "987")
    assert run.call_args[0][0][:4] == ["gh", "pr", "view", "42"]


def test_parse_github_url_pr_without_run_returns_none():
    """A PR whose checks carry no workflow run id cannot be analysed."""
    with patch("cli.analyze_ci_failure.run_command", return_value=(0, "{}", "")):
        assert parse_github_url("https://github.com/owner/repo/pull/42") is None


def test_fetch_failed_logs_returns_none_on_gh_failure():
    with patch("cli.analyze_ci_failure.run_command", return_value=(1, "", "boom")):
        assert fetch_failed_logs("owner/repo", "1") is None


def test_fetch_failed_logs_returns_stdout():
    with patch("cli.analyze_ci_failure.run_command", return_value=(0, "log text", "")):
        assert fetch_failed_logs("owner/repo", "1") == "log text"


# ── analyze_logs ──────────────────────────────────────────────────────────────


def test_analyze_logs_categorizes_each_kind_and_skips_noise():
    logs = "\n".join(
        [
            "##[group]Run tests",
            "[command]/usr/bin/gradle",
            "e: Unresolved reference: Foo",
            "npm ERR! missing script",
            "device offline",
            "AssertionError: 1 != 2",
            "Lint found 3 errors",
            "Something exception happened",
            "",
            "plain output line",
        ]
    )

    errors = analyze_logs(logs)

    assert errors["compilation"] == ["e: Unresolved reference: Foo"]
    assert errors["build"] == ["npm ERR! missing script"]
    assert errors["infrastructure"] == ["device offline"]
    assert errors["test"] == ["AssertionError: 1 != 2"]
    assert errors["lint"] == ["Lint found 3 errors"]
    assert errors["unknown"] == ["Something exception happened"]


def test_analyze_logs_deduplicates_repeated_lines():
    errors = analyze_logs("npm ERR! x\nnpm ERR! x\nweird failure\nweird failure")
    assert errors["build"] == ["npm ERR! x"]
    assert errors["unknown"] == ["weird failure"]


# ── AnalyzeCIFailureScript ────────────────────────────────────────────────────


def _run(argv, responses, capsys):
    """Run the script with run_command answering `responses` in order; return (code, stdout)."""
    with patch("cli.analyze_ci_failure.run_command", side_effect=responses):
        code = AnalyzeCIFailureScript().run(argv)
    return code, capsys.readouterr().out


def test_script_reports_missing_gh_cli(capsys):
    code, out = _run(["--run-id", "1", "--repo", "o/r"], [(1, "", "")], capsys)
    assert code == 0
    assert json.loads(out) == {"success": False, "error": "gh CLI not found"}


def test_script_rejects_invalid_url(capsys):
    _, out = _run(["--url", "https://example.com/x"], [(0, "gh 2", "")], capsys)
    assert json.loads(out)["error"] == "Invalid GitHub URL format"


def test_script_requires_url_or_run_id_and_repo(capsys):
    _, out = _run(["--run-id", "1"], [(0, "gh 2", "")], capsys)
    assert "must be provided" in json.loads(out)["error"]


def test_script_reports_log_fetch_failure(capsys):
    _, out = _run(["--run-id", "1", "--repo", "o/r"], [(0, "gh 2", ""), (1, "", "no")], capsys)
    assert json.loads(out)["error"] == "Failed to fetch logs"


def test_script_with_empty_logs_reports_zero_errors(capsys):
    _, out = _run(["--run-id", "7", "--repo", "o/r"], [(0, "gh 2", ""), (0, "  \n", "")], capsys)
    assert json.loads(out) == {"success": True, "run_id": "7", "repo": "o/r", "total_errors": 0}


def test_script_analyzes_pipeline_url_logs(capsys):
    url = "https://github.com/o/r/actions/runs/55"
    _, out = _run(["--url", url], [(0, "gh 2", ""), (0, "e: Unresolved reference: X\ndevice offline", "")], capsys)

    result = json.loads(out)
    assert result["run_id"] == "55"
    assert result["repo"] == "o/r"
    assert result["total_errors"] == 2
    assert result["priority_category"] == "compilation"
    assert result["compilation_errors"] == ["e: Unresolved reference: X"]


def test_script_summary_format(capsys):
    _, out = _run(
        ["--run-id", "9", "--repo", "o/r", "--format", "summary"],
        [(0, "gh 2", ""), (0, "npm ERR! broken", "")],
        capsys,
    )
    assert out.strip() == "[BUILD] 1 errors in run 9"


def test_format_summary_on_error():
    assert AnalyzeCIFailureScript().format_summary({"success": False, "error": "x"}) == "[ERROR] x"


def test_format_text_on_error():
    assert AnalyzeCIFailureScript().format_text({"success": False}) == "Error: Unknown error"


def _result(priority, **lists):
    base = {k: [] for k in _LISTS}
    base.update(lists)
    return {"success": True, "run_id": "3", "repo": "o/r", "total_errors": 1, "priority_category": priority, **base}


_LISTS = (
    "infrastructure_errors",
    "compilation_errors",
    "build_errors",
    "test_failures",
    "lint_errors",
    "unknown_errors",
)


def test_format_text_lists_every_category_and_truncates():
    result = _result(
        "infrastructure",
        infrastructure_errors=[f"infra {i}" for i in range(12)],
        compilation_errors=[f"comp {i}" for i in range(11)],
        build_errors=[f"build {i}" for i in range(11)],
        test_failures=[f"test {i}" for i in range(16)],
        lint_errors=[f"lint {i}" for i in range(11)],
        unknown_errors=[f"other {i}" for i in range(6)],
    )

    text = AnalyzeCIFailureScript().format_text(result)

    assert "[!] Infrastructure Errors (12 found)" in text
    assert "... and 2 more" in text  # infrastructure: 12 - 10
    assert "[!] Compilation Errors (11 found)" in text
    assert "[!] Build Errors (11 found)" in text
    assert "[!] Test Failures (16 found)" in text
    assert "[!] Lint Errors (11 found)" in text
    assert "[!] Other Errors (6 found)" in text
    assert text.count("... and 1 more") == 5  # compilation, build, test, lint, unknown
    assert "gh run rerun 3 --repo o/r" in text
    assert "View full run: https://github.com/o/r/actions/runs/3" in text


@pytest.mark.parametrize(
    "priority,advice",
    [
        ("compilation", "Fix compilation errors first"),
        ("build", "Fix build configuration"),
        ("test", "Fix failing tests"),
        ("unknown", "gh run view 3 --repo o/r --log-failed"),
    ],
)
def test_format_text_recommendation_follows_priority(priority, advice):
    assert advice in AnalyzeCIFailureScript().format_text(_result(priority))
