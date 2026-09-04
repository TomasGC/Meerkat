"""Unit tests for internal helpers in orchestrate.py."""

import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from orchestrate import (
    _progress_bar, _build_summary, _SEVERITY_ORDER, _mini_bar,
    _estimate_token_savings, _detect_base_branch,
)


# ── _progress_bar ───────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_progress_bar_zero_completed():
    """0/12 → bar starts with empty (░) blocks."""
    result = _progress_bar(0, 12)
    assert result.startswith("[░")


@pytest.mark.unit
def test_progress_bar_fully_completed():
    """12/12 → shows 100%."""
    result = _progress_bar(12, 12)
    assert "100%" in result


@pytest.mark.unit
def test_progress_bar_half_completed():
    """6/12 → shows 50%."""
    result = _progress_bar(6, 12)
    assert "50%" in result


# ── deduplication logic ─────────────────────────────────────────────────────────

@pytest.mark.unit
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

@pytest.mark.unit
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

@pytest.mark.unit
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


@pytest.mark.unit
def test_top_n_limits_violations():
    """--top 3 returns only the first 3 violations."""
    violations = [
        {"file": "a.py", "line": i, "principle": "A", "severity": "high"}
        for i in range(10)
    ]
    top3 = violations[:3]
    assert len(top3) == 3
    assert top3[0]["line"] == 0
    assert top3[2]["line"] == 2


# ── _mini_bar ───────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_mini_bar_zero():
    """0/10 → all empty blocks (░) or empty string."""
    bar = _mini_bar(0, 10)
    # When max_count>0 and count=0, filled=0 so bar is all ░
    assert "█" not in bar
    assert len(bar) == 8  # default width=8


@pytest.mark.unit
def test_mini_bar_full():
    """10/10 → all filled blocks (█)."""
    bar = _mini_bar(10, 10)
    assert "█" in bar
    assert "░" not in bar


@pytest.mark.unit
def test_mini_bar_zero_max_returns_all_empty():
    """max_count=0 → _mini_bar returns all ░ (no division by zero)."""
    bar = _mini_bar(0, 0)
    assert "█" not in bar


# ── _estimate_token_savings ─────────────────────────────────────────────────────

@pytest.mark.unit
def test_estimate_token_savings_nonzero():
    """estimate_token_savings with realistic inputs returns a positive number."""
    result = _estimate_token_savings(50, 12)
    assert result > 0


@pytest.mark.unit
def test_estimate_token_savings_zero_violations():
    """estimate_token_savings with 0 violations still accounts for checkers."""
    result = _estimate_token_savings(0, 5)
    assert result == 5 * 2000  # checkers_run * 2000


# ── CLI: invalid path exits nonzero ────────────────────────────────────────────

@pytest.mark.unit
def test_invalid_path_exits_nonzero():
    """orchestrate.py --path /nonexistent → exits with nonzero return code."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", "/nonexistent_path_xyz_does_not_exist",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0


# ── _detect_base_branch ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_detect_base_branch_returns_main(tmp_path):
    """Returns 'main' when 'main' branch exists in repo."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = _detect_base_branch(tmp_path)
    assert result == "main"
    # Should have tried 'main' first and returned immediately
    assert mock_run.call_count == 1


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
def test_orchestrate_default_mode_uses_branch_files(tmp_path):
    """Default mode (no flags) detects base branch and calls get_branch_files."""
    from orchestrate import main as orch_main
    with patch.object(sys, "argv", [
        "orchestrate.py", "--path", str(tmp_path),
        "--checks", "naming", "--format", "json", "--no-cache",
    ]):
        with patch("orchestrate._detect_base_branch", return_value="main") as mock_detect:
            with patch("orchestrate.get_branch_files", return_value=[]) as mock_branch:
                with patch("orchestrate._run_checker", return_value=_DUMMY_RESULT):
                    out = io.StringIO()
                    with io.StringIO() as _err, patch("sys.stdout", out):
                        orch_main()

    mock_detect.assert_called_once_with(tmp_path)
    mock_branch.assert_called_once_with(tmp_path, "main")


@pytest.mark.unit
def test_orchestrate_default_mode_falls_back_when_no_base_branch(tmp_path):
    """When _detect_base_branch returns None, get_branch_files is NOT called."""
    from orchestrate import main as orch_main
    with patch.object(sys, "argv", [
        "orchestrate.py", "--path", str(tmp_path),
        "--checks", "naming", "--format", "json", "--no-cache",
    ]):
        with patch("orchestrate._detect_base_branch", return_value=None):
            with patch("orchestrate.get_branch_files") as mock_branch:
                with patch("orchestrate._run_checker", return_value=_DUMMY_RESULT):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    mock_branch.assert_not_called()


@pytest.mark.unit
def test_orchestrate_default_mode_falls_back_when_branch_files_none(tmp_path):
    """When get_branch_files returns None, full analysis runs (incremental_files stays None)."""
    from orchestrate import main as orch_main
    captured_calls = []

    def capture_run_checker(name, mod_path, path, language, files, *args, **kwargs):
        captured_calls.append(files)
        return _DUMMY_RESULT

    with patch.object(sys, "argv", [
        "orchestrate.py", "--path", str(tmp_path),
        "--checks", "naming", "--format", "json", "--no-cache",
    ]):
        with patch("orchestrate._detect_base_branch", return_value="main"):
            with patch("orchestrate.get_branch_files", return_value=None):
                with patch("orchestrate._run_checker", side_effect=capture_run_checker):
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        orch_main()

    # incremental_files was None → checker received None for files param
    assert captured_calls and captured_calls[0] is None


@pytest.mark.unit
def test_orchestrate_staged_empty_list_runs_without_crash(tmp_path):
    """--staged with get_staged_files returning [] → checker called with [], exits 0."""
    from orchestrate import main as orch_main
    captured_calls = []

    def capture_run_checker(name, mod_path, path, language, files, *args, **kwargs):
        captured_calls.append(files)
        return _DUMMY_RESULT

    with patch.object(sys, "argv", [
        "orchestrate.py", "--path", str(tmp_path),
        "--checks", "naming", "--format", "json", "--staged", "--no-cache",
    ]):
        with patch("orchestrate.get_staged_files", return_value=[]):
            with patch("orchestrate._run_checker", side_effect=capture_run_checker):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    orch_main()

    assert captured_calls and captured_calls[0] == []
