"""Unit tests for internal helpers in orchestrate.py."""

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"

from cca.orchestrate import (
    _build_summary,
    _detect_base_branch,
    _estimate_token_savings,
    _mini_bar,
    _progress_bar,
)
from lib.engine.orchestrator import _SEVERITY_ORDER, _print_table

# ── _progress_bar ───────────────────────────────────────────────────────────────


def test_progress_bar_zero_completed():
    """0/12 → bar starts with empty (░) blocks."""
    result = _progress_bar(0, 12)
    assert result.startswith("[░")


def test_progress_bar_fully_completed():
    """12/12 → shows 100%."""
    result = _progress_bar(12, 12)
    assert "100%" in result


def test_progress_bar_half_completed():
    """6/12 → shows 50%."""
    result = _progress_bar(6, 12)
    assert "50%" in result


# ── deduplication logic ─────────────────────────────────────────────────────────


def test_deduplication_removes_duplicate_key():
    """Violations with same (file, line, principle) are deduplicated."""
    v1 = {"file": "a.py", "line": 5, "principle": "Naming", "severity": "high"}
    v2 = {"file": "a.py", "line": 5, "principle": "Naming", "severity": "high"}  # duplicate
    v3 = {"file": "a.py", "line": 10, "principle": "Naming", "severity": "medium"}

    results = [
        {"violations": [v1, v2]},
        {"violations": [v3]},
    ]

    # Replicate orchestrate.py dedup logic
    all_violations = []
    seen = set()
    for result in results:
        for v in result.get("violations", []):
            key = (v.get("file"), v.get("line"), v.get("principle"))
            if key not in seen:
                seen.add(key)
                all_violations.append(v)

    assert len(all_violations) == 2


# ── _build_summary ──────────────────────────────────────────────────────────────


def test_build_summary_counts_severities():
    """3 high + 2 medium + 1 low → correct counts in summary."""
    results = [
        {
            "principle": "Naming",
            "violations": [
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "medium"},
                {"severity": "medium"},
                {"severity": "low"},
            ],
        }
    ]
    summary = _build_summary(results)
    assert summary["Naming"]["count"] == 6
    assert summary["Naming"]["high"] == 3
    assert summary["Naming"]["medium"] == 2
    assert summary["Naming"]["low"] == 1


# ── filtering ───────────────────────────────────────────────────────────────────


def test_min_severity_high_removes_medium_and_low():
    """--min-severity high filter removes medium and low violations."""
    violations = [
        {"file": "a.py", "line": 1, "principle": "A", "severity": "high"},
        {"file": "a.py", "line": 2, "principle": "A", "severity": "medium"},
        {"file": "a.py", "line": 3, "principle": "A", "severity": "low"},
    ]
    min_sev = _SEVERITY_ORDER.get("high", 0)
    filtered = [v for v in violations if _SEVERITY_ORDER.get(v.get("severity", "low"), 2) <= min_sev]
    assert len(filtered) == 1
    assert filtered[0]["severity"] == "high"


def test_top_n_limits_violations():
    """--top 3 returns only the first 3 violations."""
    violations = [{"file": "a.py", "line": i, "principle": "A", "severity": "high"} for i in range(10)]
    top3 = violations[:3]
    assert len(top3) == 3
    assert top3[0]["line"] == 0
    assert top3[2]["line"] == 2


# ── _mini_bar ───────────────────────────────────────────────────────────────────


def test_mini_bar_zero():
    """0/10 → all empty blocks (░) or empty string."""
    bar = _mini_bar(0, 10)
    # When max_count>0 and count=0, filled=0 so bar is all ░
    assert "█" not in bar
    assert len(bar) == 8  # default width=8


def test_mini_bar_full():
    """10/10 → all filled blocks (█)."""
    bar = _mini_bar(10, 10)
    assert "█" in bar
    assert "░" not in bar


def test_mini_bar_zero_max_returns_all_empty():
    """max_count=0 → _mini_bar returns all ░ (no division by zero)."""
    bar = _mini_bar(0, 0)
    assert "█" not in bar


# ── _estimate_token_savings ─────────────────────────────────────────────────────


def test_estimate_token_savings_nonzero():
    """estimate_token_savings with realistic inputs returns a positive number."""
    result = _estimate_token_savings(50, 12)
    assert result > 0


def test_estimate_token_savings_zero_violations():
    """estimate_token_savings with 0 violations still accounts for checkers."""
    result = _estimate_token_savings(0, 5)
    assert result == 5 * 2000  # checkers_run * 2000


# ── CLI: invalid path exits nonzero ────────────────────────────────────────────


def test_invalid_path_exits_nonzero():
    """orchestrate.py --path /nonexistent → exits with nonzero return code."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path",
            "/nonexistent_path_xyz_does_not_exist",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0


# ── _detect_base_branch ─────────────────────────────────────────────────────────


def test_detect_base_branch_returns_main(tmp_path):
    """Returns 'main' when 'main' branch exists in repo."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = _detect_base_branch(tmp_path)
    assert result == "main"
    # Should have tried 'main' first and returned immediately
    assert mock_run.call_count == 1


def test_detect_base_branch_falls_back_to_master(tmp_path):
    """Returns 'master' when 'main' is absent but 'master' exists."""

    def side_effect(cmd, **kwargs):
        branch = cmd[-1]  # last arg is branch name
        mock = MagicMock()
        mock.returncode = 0 if branch == "master" else 1
        return mock

    with patch("subprocess.run", side_effect=side_effect):
        result = _detect_base_branch(tmp_path)
    assert result == "master"


def test_detect_base_branch_returns_none_when_neither(tmp_path):
    """Returns None when neither 'main' nor 'master' exists."""
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        result = _detect_base_branch(tmp_path)
    assert result is None


# ── orchestrate default mode (branch-vs-main) ──────────────────────────────────

_DUMMY_RESULT = {
    "principle": "Naming",
    "success": True,
    "violations": [],
    "files_analyzed": 0,
    "duration_ms": 1,
}


def test_orchestrate_default_mode_uses_branch_files(tmp_path):
    """Default mode (no flags) detects base branch and calls get_branch_files."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator._detect_base_branch", return_value="main") as mock_detect:
            with patch("lib.engine.orchestrator.get_branch_files", return_value=[]) as mock_branch:
                with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
                    out = io.StringIO()
                    with io.StringIO() as _err, patch("sys.stdout", out):
                        orch_main()

    mock_detect.assert_called_once_with(tmp_path)
    mock_branch.assert_called_once_with(tmp_path, "main")


def test_orchestrate_default_mode_falls_back_when_no_base_branch(tmp_path):
    """When _detect_base_branch returns None, get_branch_files is NOT called."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator._detect_base_branch", return_value=None):
            with patch("lib.engine.orchestrator.get_branch_files") as mock_branch:
                with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    mock_branch.assert_not_called()


def test_orchestrate_default_mode_falls_back_when_branch_files_none(tmp_path):
    """When get_branch_files returns None, full analysis runs over every discovered file."""
    from cca.orchestrate import main as orch_main

    (tmp_path / "mod.py").write_text("x = 1\n")
    captured_calls = []

    def capture_run_checker(name, mod_path, path, language, files, *args, **kwargs):
        captured_calls.append(files)
        return _DUMMY_RESULT

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator._detect_base_branch", return_value="main"):
            with patch("lib.engine.orchestrator.get_branch_files", return_value=None):
                with patch("lib.engine.orchestrator._run_checker", side_effect=capture_run_checker):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    # Full mode: the orchestrator discovers the files and hands each language its own group
    assert captured_calls == [[tmp_path / "mod.py"]]


def test_orchestrate_staged_empty_list_runs_without_crash(tmp_path):
    """--staged with nothing staged → no language group, so no checker run; still valid JSON."""
    from cca.orchestrate import main as orch_main

    captured_calls = []

    def capture_run_checker(name, mod_path, path, language, files, *args, **kwargs):
        captured_calls.append(files)
        return _DUMMY_RESULT

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--staged",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator.get_staged_files", return_value=[]):
            with patch("lib.engine.orchestrator._run_checker", side_effect=capture_run_checker):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    orch_main()

    assert captured_calls == []
    assert json.loads(out.getvalue())["total_violations"] == 0


# ── _print_table ─────────────────────────────────────────────────────────────────


def test_print_table_empty_prints_no_violations():
    """_print_table([], "principle") → prints 'No violations found.'"""
    out = io.StringIO()
    with patch("sys.stdout", out):
        _print_table([], "principle")
    assert "No violations found" in out.getvalue()


def test_print_table_with_violations_prints_header_and_row():
    """_print_table with one violation → prints SEVERITY header and file info."""
    violations = [{"severity": "high", "principle": "Naming", "file": "a.py", "line": 5, "message": "bad name"}]
    out = io.StringIO()
    with patch("sys.stdout", out):
        _print_table(violations, "principle")
    output = out.getvalue()
    assert "SEVERITY" in output
    assert "a.py" in output


# ── _run_checker: exception path ─────────────────────────────────────────────────


def test_run_checker_exception_returns_error_dict(tmp_path):
    """_run_checker with nonexistent module → returns error dict with success=False."""
    from cca.orchestrate import _run_checker

    result = _run_checker("TestPrinciple", "nonexistent.checker.module.xyz", tmp_path, "python")
    assert result["success"] is False
    assert result["principle"] == "TestPrinciple"
    assert "error" in result
    assert result["violations"] == []


# ── --fast flag ──────────────────────────────────────────────────────────────────


def test_orchestrate_fast_flag_sets_model_to_fast(tmp_path):
    """--fast passes role="fast" to _run_checker instead of a hardcoded model name."""
    from cca.orchestrate import main as orch_main

    (tmp_path / "mod.py").write_text("x = 1\n")
    captured_model = []

    def capture_checker(name, mod_path, path, language, files, agents, no_cache, cache_ttl, model, cache_dir=None):
        captured_model.append(model)
        return _DUMMY_RESULT

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
            "--fast",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", side_effect=capture_checker):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    assert captured_model and captured_model[0] == "fast"


# ── --clear-cache ────────────────────────────────────────────────────────────────


def test_orchestrate_clear_cache_calls_clear_and_exits(tmp_path):
    """--clear-cache clears cache and sys.exit(0)."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--clear-cache",
        ],
    ):
        with patch("lib.engine.orchestrator.clear_cache", return_value=3) as mock_clear:
            with pytest.raises(SystemExit) as exc_info:
                orch_main()

    mock_clear.assert_called_once()
    assert exc_info.value.code == 0


# ── unknown checker warning ──────────────────────────────────────────────────────


def test_orchestrate_unknown_checker_prints_warning(tmp_path):
    """Unknown checker name in --checks → warning printed to stderr."""
    from cca.orchestrate import main as orch_main

    err = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "nonexistent_checker_xyz,naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
            with patch("sys.stderr", err):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    orch_main()

    assert "Unknown" in err.getvalue() or "WARN" in err.getvalue()


# ── --format table ────────────────────────────────────────────────────────────────


def test_orchestrate_format_table_prints_header(tmp_path):
    """--format table → table header printed (not JSON output)."""
    from cca.orchestrate import main as orch_main

    out = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "table",
            "--no-cache",
            "--full",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
            with patch("sys.stdout", out):
                orch_main()

    output = out.getvalue()
    # Table format prints the analysis header line
    assert "Clean Code Analysis" in output or "Violations" in output


# ── --output file ─────────────────────────────────────────────────────────────────


def test_orchestrate_output_file_writes_json(tmp_path):
    """--output writes JSON results to file instead of stdout."""
    from cca.orchestrate import main as orch_main

    output_path = tmp_path / "results.json"
    err = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
            "--output",
            str(output_path),
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
            with patch("sys.stderr", err):
                orch_main()

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert "violations" in data


# ── --agents 2 ───────────────────────────────────────────────────────────────────


def test_orchestrate_agents_2_prints_message(tmp_path):
    """--agents 2 → message about multi-agent mode printed to stderr."""
    from cca.orchestrate import main as orch_main

    err = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
            "--agents",
            "2",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
            with patch("sys.stderr", err):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    orch_main()

    assert "agent" in err.getvalue().lower() or "2x" in err.getvalue()


# ── --top N limits violations ────────────────────────────────────────────────────


def test_orchestrate_top_limits_output(tmp_path):
    """--top 1 limits violations in output to 1."""
    from cca.orchestrate import main as orch_main

    dummy_2 = {
        **_DUMMY_RESULT,
        "violations": [
            {"file": "a.py", "line": 1, "principle": "Naming", "severity": "high", "message": "v1"},
            {"file": "a.py", "line": 2, "principle": "Naming", "severity": "high", "message": "v2"},
        ],
    }
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
            "--top",
            "1",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=dummy_2):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    data = json.loads(out.getvalue())
    assert data["total_violations"] <= 1


# ── cache_hits display ────────────────────────────────────────────────────────────


def test_orchestrate_cache_hits_added_to_output(tmp_path):
    """checker result with cache_hits > 0 → cache key in JSON output."""
    from cca.orchestrate import main as orch_main

    (tmp_path / "mod.py").write_text("x = 1\n")
    dummy_cached = {**_DUMMY_RESULT, "cache_hits": 5, "cache_total": 10}
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=dummy_cached):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    data = json.loads(out.getvalue())
    assert "cache" in data
    assert data["cache"]["hits"] == 5


# ── on_checker_done: exception path ──────────────────────────────────────────────


def test_orchestrate_checker_future_exception_handled(tmp_path):
    """Checker that raises exception → on_checker_done catches it, success=False result."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", side_effect=RuntimeError("checker exploded")):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    data = json.loads(out.getvalue())
    assert "violations" in data  # still returns valid structure


# ── _run_checker: successful kwargs-building path ────────────────────────────────


def test_run_checker_success_with_files_param(tmp_path):
    """_run_checker with real checker module and files param → success=True."""
    from cca.orchestrate import _run_checker

    f = tmp_path / "mod.py"
    f.write_text("x = 1\n")
    result = _run_checker(
        "Naming",
        "cca.checkers.check_naming",
        tmp_path,
        "python",
        files=[f],
        agents=1,
        no_cache=True,
        cache_ttl_days=7,
        role=None,
    )
    assert result["success"] is True
    assert result["principle"] == "Naming"
    assert "violations" in result


def test_run_checker_success_no_files(tmp_path):
    """_run_checker with files=None → success=True (full directory scan)."""
    from cca.orchestrate import _run_checker

    (tmp_path / "mod.py").write_text("x = 1\n")
    result = _run_checker(
        "Naming",
        "cca.checkers.check_naming",
        tmp_path,
        "python",
        files=None,
        agents=1,
        no_cache=True,
        cache_ttl_days=7,
        role=None,
    )
    assert result["success"] is True


# ── orchestrate --checks all (line 213) ─────────────────────────────────────────


def test_orchestrate_checks_all_runs_all_checkers(tmp_path):
    """Default --checks all → selected contains all CHECKERS entries."""
    from cca.orchestrate import CHECKERS
    from cca.orchestrate import main as orch_main

    (tmp_path / "mod.py").write_text("x = 1\n")
    call_count = [0]

    def count_checker(*args, **kwargs):
        call_count[0] += 1
        return _DUMMY_RESULT

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--format",
            "json",
            "--no-cache",
            "--full",
            # no --checks → defaults to "all"
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", side_effect=count_checker):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    assert call_count[0] == len(CHECKERS)


# ── orchestrate path not found (lines 209-210) ──────────────────────────────────


def test_orchestrate_path_not_found_exits_1(tmp_path):
    """--path nonexistent → sys.exit(1) in-process."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            "/path_that_does_not_exist_xyz123abc",
        ],
    ):
        with pytest.raises(SystemExit) as exc:
            orch_main()
    assert exc.value.code == 1


# ── orchestrate --staged returns None (line 230) ────────────────────────────────


def test_orchestrate_staged_not_git_repo_fallback(tmp_path):
    """--staged when get_staged_files returns None → fallback to full analysis."""
    from cca.orchestrate import main as orch_main

    err = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--staged",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator.get_staged_files", return_value=None):
            with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
                with patch("sys.stderr", err):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    stderr_text = err.getvalue().lower()
    assert "full analysis" in stderr_text or "not a git" in stderr_text


# ── orchestrate --since (lines 232-237) ─────────────────────────────────────────


def test_orchestrate_since_flag_calls_get_changed_files(tmp_path):
    """--since HEAD~1 → calls get_changed_files with since arg."""
    from cca.orchestrate import main as orch_main

    err = io.StringIO()
    f = tmp_path / "mod.py"
    f.write_text("x = 1\n")

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--since",
            "HEAD~1",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator.get_changed_files", return_value=[f]) as mock_changed:
            with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
                with patch("sys.stderr", err):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    mock_changed.assert_called_once_with(tmp_path, since="HEAD~1")


def test_orchestrate_since_not_git_repo_fallback(tmp_path):
    """--since when get_changed_files returns None → full analysis fallback message."""
    from cca.orchestrate import main as orch_main

    err = io.StringIO()
    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--since",
            "main",
            "--no-cache",
        ],
    ):
        with patch("lib.engine.orchestrator.get_changed_files", return_value=None):
            with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
                with patch("sys.stderr", err):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    stderr_text = err.getvalue().lower()
    assert "full analysis" in stderr_text or "not a git" in stderr_text


# ── _run_checker: model + cache_ttl_days kwargs passed (lines 101, 103) ──────────


def test_run_checker_model_kwarg_passed_to_run(tmp_path):
    """_run_checker passes role kwarg when checker run() accepts it."""
    from cca.orchestrate import _run_checker

    captured = {}

    def fake_run(path, language, files=None, agents=1, no_cache=False, role="default"):
        captured["role"] = role
        return {"violations": [], "files_analyzed": 0, "success": True}

    import types

    fake_module = types.ModuleType("cca.checkers.check_solid_fake")
    fake_module.run = fake_run

    with patch("lib.engine.orchestrator.importlib.import_module", return_value=fake_module):
        result = _run_checker(
            "SOLID",
            "cca.checkers.check_solid_fake",
            tmp_path,
            "python",
            files=None,
            agents=1,
            no_cache=True,
            cache_ttl_days=7,
            role="analyzer",
        )

    assert captured.get("role") == "analyzer"
    assert result["success"] is True


def test_run_checker_cache_ttl_days_kwarg_passed_to_run(tmp_path):
    """_run_checker passes cache_ttl_days kwarg when checker run() accepts it (line 101)."""
    from cca.orchestrate import _run_checker

    captured = {}

    def fake_run(path, language, files=None, agents=1, no_cache=False, cache_ttl_days=30):
        captured["cache_ttl_days"] = cache_ttl_days
        return {"violations": [], "files_analyzed": 0, "success": True}

    import types

    fake_module = types.ModuleType("cca.checkers.check_fake_ttl")
    fake_module.run = fake_run

    with patch("lib.engine.orchestrator.importlib.import_module", return_value=fake_module):
        result = _run_checker(
            "Fake",
            "cca.checkers.check_fake_ttl",
            tmp_path,
            "python",
            files=None,
            agents=1,
            no_cache=True,
            cache_ttl_days=14,
            role=None,
        )

    assert captured.get("cache_ttl_days") == 14
    assert result["success"] is True


def _fake_checker_module(name: str, run_fn):
    import types

    mod = types.ModuleType(name)
    mod.run = run_fn
    return mod


def test_run_checker_cache_dir_passed_when_declared(tmp_path):
    """_run_checker forwards cache_dir only to a checker whose run() declares it."""
    from cca.orchestrate import _run_checker

    captured = {}

    def fake_run(path, language, files=None, cache_dir=None):
        captured["cache_dir"] = cache_dir
        return {"violations": [], "files_analyzed": 0, "success": True}

    with patch(
        "lib.engine.orchestrator.importlib.import_module",
        return_value=_fake_checker_module("cca.checkers.fake_cached", fake_run),
    ):
        _run_checker("Fake", "cca.checkers.fake_cached", tmp_path, "python", cache_dir=tmp_path / "c")

    assert captured["cache_dir"] == tmp_path / "c"


def test_run_checker_cache_dir_not_passed_when_undeclared(tmp_path):
    """A checker without cache_dir in its run() signature is called without it.

    An unexpected keyword would raise TypeError inside run(), which _run_checker
    turns into success=False — so success=True proves cache_dir was withheld.
    """
    from cca.orchestrate import _run_checker

    def fake_run(path, language, files=None):
        return {"violations": [], "files_analyzed": 0, "success": True}

    with patch(
        "lib.engine.orchestrator.importlib.import_module",
        return_value=_fake_checker_module("cca.checkers.fake_plain", fake_run),
    ):
        result = _run_checker("Fake", "cca.checkers.fake_plain", tmp_path, "python", cache_dir=tmp_path / "c")

    assert result["success"] is True, result.get("error")


_AI_CHECKERS = ["check_solid", "check_cqrs", "check_ddd", "check_slap", "check_kiss", "check_yagni"]
_MECHANICAL_CHECKERS = ["check_dry", "check_naming", "check_comments", "check_lod", "check_inheritance"]


@pytest.mark.parametrize("checker", _AI_CHECKERS)
def test_ai_checker_forwards_cache_dir_and_ttl_to_run_hybrid(tmp_path, checker):
    """Every AI-backed CCA checker hands cache_dir and cache_ttl_days to run_hybrid."""
    import importlib

    mod = importlib.import_module(f"cca.checkers.{checker}")
    with patch.object(mod, "run_hybrid", return_value=_DUMMY_RESULT) as hybrid:
        if hasattr(mod, "check_server_available"):
            with patch.object(mod, "check_server_available", return_value=True):
                mod.run(tmp_path, "python", cache_dir=tmp_path / "c", cache_ttl_days=3)
        else:
            mod.run(tmp_path, "python", cache_dir=tmp_path / "c", cache_ttl_days=3)
    kwargs = hybrid.call_args.kwargs
    assert (kwargs["cache_dir"], kwargs["cache_ttl_days"]) == (tmp_path / "c", 3)


@pytest.mark.parametrize("checker", _MECHANICAL_CHECKERS)
def test_mechanical_checker_does_not_declare_cache_dir(checker):
    """Mechanical-only checkers have no AI pass to cache, so the orchestrator withholds cache_dir."""
    import importlib
    import inspect

    params = inspect.signature(importlib.import_module(f"cca.checkers.{checker}").run).parameters
    assert "cache_dir" not in params


def test_main_passes_agent_cache_dir_to_run_checker(tmp_path):
    """CCA's cca.orchestrate.main() hands its own cache directory to every _run_checker call."""
    import cca.orchestrate

    (tmp_path / "mod.py").write_text("x = 1\n")
    seen = []

    def capture(*args, **kwargs):
        seen.append(args[-1])
        return _DUMMY_RESULT

    with patch.object(sys, "argv", ["orchestrate.py", "--path", str(tmp_path), "--checks", "naming", "--full"]):
        with patch("lib.engine.orchestrator._run_checker", side_effect=capture):
            with patch("builtins.print"):
                cca.orchestrate.main()

    assert seen == [cca.orchestrate._CACHE_DIR]


def test_main_uses_cca_cache_dir_env_var_when_set(tmp_path, monkeypatch):
    """CCA_CACHE_DIR, read at main() call time, becomes the engine's cache_dir."""
    import cca.orchestrate

    override = tmp_path / "cca-cache"
    monkeypatch.setenv("CCA_CACHE_DIR", str(override))

    with patch("cca.orchestrate._engine_main") as engine_main:
        cca.orchestrate.main()

    assert engine_main.call_args.kwargs["cache_dir"] == override


def test_main_uses_default_cache_dir_when_env_var_unset(monkeypatch):
    """Without CCA_CACHE_DIR the engine gets the default _CACHE_DIR."""
    import cca.orchestrate

    monkeypatch.delenv("CCA_CACHE_DIR", raising=False)

    with patch("cca.orchestrate._engine_main") as engine_main:
        cca.orchestrate.main()

    assert engine_main.call_args.kwargs["cache_dir"] == cca.orchestrate._CACHE_DIR


# ── __main__ guard (line 392) ────────────────────────────────────────────────────


def test_main_entrypoint_callable(tmp_path):
    """cca.orchestrate.main() is callable directly (covers the __main__ guard path)."""
    from cca.orchestrate import main as orch_main

    with patch.object(
        sys,
        "argv",
        [
            "orchestrate.py",
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
        ],
    ):
        with patch("lib.engine.orchestrator._run_checker", return_value=_DUMMY_RESULT):
            out = io.StringIO()
            with patch("sys.stdout", out):
                orch_main()

    assert out.getvalue()  # produced some output


def test_orchestrate_as_main_script(tmp_path):
    """Run orchestrate.py as __main__ (subprocess) → covers line 392."""
    import subprocess

    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    orchestrate_path = scripts_dir / "orchestrate.py"
    result = subprocess.run(
        [
            sys.executable,
            str(orchestrate_path),
            "--path",
            str(tmp_path),
            "--checks",
            "naming",
            "--format",
            "json",
            "--no-cache",
            "--full",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert result.stdout  # produced JSON output
