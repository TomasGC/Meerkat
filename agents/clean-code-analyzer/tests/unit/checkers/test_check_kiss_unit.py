"""Unit tests for checkers/check_kiss.py — mocks complexity subprocess and local AI.

check_kiss.run() delegates to lib.engine.hybrid.run_hybrid() with a mechanical_fn
that shells out to calculate_complexity.py. The mechanical subprocess call still
lives on the checker module (_CALC_COMPLEXITY, subprocess.run), so those patch
targets are unchanged. The AI pass (availability guard + analyze_files_parallel +
discover_files for the default/no-files path) now lives inside run_hybrid, so
those are patched on lib.engine.hybrid, where the real call sites are.
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import cca.checkers.check_kiss as kiss_mod
from cca.checkers.check_kiss import run

_HYBRID_CHECK_AVAILABLE = "lib.engine.hybrid.check_server_available"
_HYBRID_ANALYZE_PARALLEL = "lib.engine.hybrid.analyze_files_parallel"
_HYBRID_DISCOVER_FILES = "lib.engine.hybrid.discover_files"

HIGH_COMPLEXITY_OUTPUT = json.dumps(
    {
        "files_analyzed": 1,
        "complexity_issues": [
            {
                "file": "app.py",
                "function": "process_data",
                "line": 10,
                "cyclomatic_complexity": 15,
                "nesting_depth": 4,
                "lines": 80,
                "severity": "high",
            }
        ],
    }
)

LOW_COMPLEXITY_OUTPUT = json.dumps(
    {
        "files_analyzed": 1,
        "complexity_issues": [],
    }
)


@pytest.fixture
def mocked_calc_complexity():
    """Patch _CALC_COMPLEXITY to claim it exists."""
    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path:
        mock_path.exists.return_value = True
        yield mock_path


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_high_complexity_creates_violation(tmp_path):
    """High-complexity function → KISS violation created from subprocess output."""
    (tmp_path / "app.py").write_text("def process_data(): pass\n")

    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) >= 1
    assert any(v["principle"] == "KISS" for v in result["violations"])


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_low_complexity_no_violation(tmp_path):
    """Low complexity → no complexity violations."""
    (tmp_path / "app.py").write_text("def simple(): return 1\n")

    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_ollama_called_only_when_available(tmp_path):
    """analyze_files_parallel is only called when check_server_available=True."""
    (tmp_path / "app.py").write_text("class Foo: pass\n")

    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[]
    ) as mock_ollama:
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        run(tmp_path, "python")

    mock_ollama.assert_called_once()


def test_kiss_subprocess_failure_graceful(tmp_path):
    """Subprocess failure → graceful empty result, success=True (complexity part skipped)."""
    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, patch("subprocess.run") as mock_run, patch(
        _HYBRID_CHECK_AVAILABLE, return_value=False
    ):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


def test_kiss_subprocess_timeout_graceful(tmp_path):
    """subprocess.TimeoutExpired → graceful empty result (exception path)."""
    import subprocess

    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)
    ), patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_path.exists.return_value = True
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


def test_kiss_subprocess_json_decode_error_graceful(tmp_path):
    """subprocess returns invalid JSON → JSONDecodeError caught, empty violations."""
    (tmp_path / "app.py").write_text("def f(): pass\n")

    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, patch("subprocess.run") as mock_run, patch(
        _HYBRID_CHECK_AVAILABLE, return_value=False
    ):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="{ invalid json }", stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_incremental_files_filter_by_name(tmp_path):
    """In incremental mode (files=[...]), complexity issues are filtered to changed files."""
    targeted = tmp_path / "targeted.py"
    targeted.write_text("def process_data(): pass\n")
    other = tmp_path / "other.py"
    other.write_text("def simple(): pass\n")

    # Subprocess returns violations for both files but only targeted is in incremental list
    both_files_output = json.dumps(
        {
            "files_analyzed": 2,
            "complexity_issues": [
                {
                    "file": "targeted.py",
                    "function": "process_data",
                    "cyclomatic_complexity": 15,
                    "nesting_depth": 4,
                    "lines": 80,
                    "severity": "high",
                },
                {
                    "file": "other.py",
                    "function": "simple",
                    "cyclomatic_complexity": 15,
                    "nesting_depth": 4,
                    "lines": 80,
                    "severity": "high",
                },
            ],
        }
    )
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=both_files_output, stderr="")
        result = run(tmp_path, "python", files=[targeted])

    # Only targeted.py violation should be included
    for v in result["violations"]:
        assert "targeted" in v["file"] or "targeted" in v.get("file", "")


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_ollama_violation_appended(tmp_path):
    """Ollama returns violation → appended to violations list with principle=KISS.

    Mechanical layer is mocked to LOW_COMPLEXITY_OUTPUT (zero findings), so there
    is nothing for the AI finding to reconcile against — this test is about the
    AI layer surfacing a violation on its own, not about the two layers coexisting.
    """
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    def get_user(self): pass\n")

    ollama_item = {
        "source_file": str(f),
        "source_file_name": f.name,
        "pattern": "OverEngineering",
        "violation": "Over-abstracted service",
        "severity": "medium",
        "suggestion": "Simplify",
        "line": 1,
    }
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[ollama_item]
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=None)

    kiss_v = [v for v in result["violations"] if v["principle"] == "KISS"]
    assert len(kiss_v) >= 1
    assert "OverEngineering" in kiss_v[0]["message"]


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_files_not_none_ollama_path(tmp_path):
    """files is not None + Ollama available → select_files() honours the explicit list."""
    f = tmp_path / "service.py"
    f.write_text("class X: pass\n")

    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[]
    ) as mock_ollama:
        mock_run.return_value = MagicMock(returncode=0, stdout=LOW_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=[f])

    mock_ollama.assert_called_once()
    assert result["success"] is True


def test_kiss_files_analyzed_zero_gets_set_from_source_files(tmp_path):
    """files_analyzed=0 after complexity part → set from discovered source_files."""
    f = tmp_path / "service.py"
    f.write_text("class X: pass\n")

    # Return output with files_analyzed=0 to leave files_analyzed=0 after complexity
    empty_output = json.dumps({"files_analyzed": 0, "complexity_issues": []})
    with patch.object(kiss_mod, "_CALC_COMPLEXITY") as mock_path, patch("subprocess.run") as mock_run, patch(
        _HYBRID_CHECK_AVAILABLE, return_value=True
    ), patch(_HYBRID_DISCOVER_FILES, return_value=[f]), patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]):
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=empty_output, stderr="")
        result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    assert result["files_analyzed"] >= 1  # set from source_files


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_ai_finding_near_mechanical_dropped(tmp_path):
    """AI finding within 3 lines of a mechanical finding in the same file is dropped as a near-duplicate."""
    f = tmp_path / "app.py"
    f.write_text("def process_data(): pass\n")

    ollama_item = {
        "source_file": str(f),
        "pattern": "OverEngineering",
        "violation": "Duplicate of mechanical finding",
        "severity": "medium",
        "suggestion": "Simplify",
        "line": 11,  # within 3 lines of the mechanical finding's line=10
    }
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[ollama_item]
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    assert len(result["violations"]) == 1
    assert "High complexity" in result["violations"][0]["message"]


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_ai_finding_far_from_mechanical_both_kept(tmp_path):
    """AI finding more than 3 lines from a mechanical finding in the same file survives reconciliation."""
    f = tmp_path / "app.py"
    f.write_text("def process_data(): pass\n" * 40)

    ollama_item = {
        "source_file": str(f),
        "pattern": "OverEngineering",
        "violation": "Unrelated over-engineering elsewhere in the file",
        "severity": "medium",
        "suggestion": "Simplify",
        "line": 30,  # far from the mechanical finding's line=10
    }
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[ollama_item]
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    assert len(result["violations"]) == 2
    messages = [v["message"] for v in result["violations"]]
    assert any("High complexity" in m for m in messages)
    assert any("OverEngineering" in m for m in messages)


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_complexity_violation_carries_def_line(tmp_path):
    """The mechanical violation's line comes from calculate_complexity's `line` field."""
    (tmp_path / "app.py").write_text("def process_data(): pass\n")

    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python")

    assert [v["line"] for v in result["violations"]] == [10]


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_ai_finding_on_line_1_kept_when_mechanical_at_line_10(tmp_path):
    """An AI finding near the top of the file is no longer swallowed by a line-0 mechanical hit."""
    f = tmp_path / "app.py"
    f.write_text("def process_data(): pass\n" * 20)

    ollama_item = {
        "source_file": str(f),
        "pattern": "OverEngineering",
        "violation": "Unrelated finding at the top of the file",
        "severity": "medium",
        "suggestion": "Simplify",
        "line": 1,
    }
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=True), patch(
        _HYBRID_ANALYZE_PARALLEL, return_value=[ollama_item]
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=HIGH_COMPLEXITY_OUTPUT, stderr="")
        result = run(tmp_path, "python", files=None)

    lines = sorted(v["line"] for v in result["violations"])
    assert lines == [1, 10]


@pytest.mark.usefixtures("mocked_calc_complexity")
def test_kiss_two_complexity_issues_same_file_distinct_lines(tmp_path):
    """Two complexity hits in one file keep distinct lines, so (file, line, principle) dedup keeps both."""
    (tmp_path / "app.py").write_text("def a(): pass\n")
    two_issues = json.dumps(
        {
            "files_analyzed": 1,
            "complexity_issues": [
                {
                    "file": "app.py",
                    "function": "first",
                    "line": 10,
                    "cyclomatic_complexity": 15,
                    "nesting_depth": 4,
                    "lines": 80,
                    "severity": "high",
                },
                {
                    "file": "app.py",
                    "function": "second",
                    "line": 120,
                    "cyclomatic_complexity": 12,
                    "nesting_depth": 4,
                    "lines": 60,
                    "severity": "medium",
                },
            ],
        }
    )
    with patch("subprocess.run") as mock_run, patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
        mock_run.return_value = MagicMock(returncode=0, stdout=two_issues, stderr="")
        result = run(tmp_path, "python")

    keys = {(v["file"], v["line"], v["principle"]) for v in result["violations"]}
    assert keys == {("app.py", 10, "KISS"), ("app.py", 120, "KISS")}


def test_tool_failure_warns_on_stderr_and_still_runs_ai(tmp_path, capsys):
    """calculate_complexity.py failing is reported once on stderr; the AI pass still runs."""
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")
    ai_item = {
        "line": 1,
        "pattern": "complex-solution",
        "violation": "v",
        "suggestion": "s",
        "source_file": str(tmp_path / "app.py"),
    }
    with patch("cca.checkers.check_kiss._CALC_COMPLEXITY") as mock_path:
        mock_path.exists.return_value = True
        mock_path.name = "calculate_complexity.py"
        with patch("subprocess.run", return_value=MagicMock(returncode=2, stdout="", stderr="boom")):
            with patch("lib.engine.hybrid.check_server_available", return_value=True):
                with patch("lib.engine.hybrid.analyze_files_parallel", return_value=[ai_item]):
                    result = run(tmp_path, "python")

    warnings = [line for line in capsys.readouterr().err.splitlines() if line.startswith("[WARN]")]
    assert warnings == ["[WARN] KISS: calculate_complexity.py failed: boom"]
    assert result["success"] is True
    assert [v["line"] for v in result["violations"]] == [1]


@pytest.mark.parametrize(
    "side_effect, run_result, expected",
    [
        (subprocess.TimeoutExpired("cmd", 60), None, "TimeoutExpired"),
        (None, MagicMock(returncode=0, stdout="{not json", stderr=""), "JSONDecodeError"),
    ],
)
def test_tool_exception_warns_on_stderr(tmp_path, capsys, side_effect, run_result, expected):
    """A timeout or malformed tool output is reported on stderr, not swallowed."""
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")
    with patch("cca.checkers.check_kiss._CALC_COMPLEXITY") as mock_path:
        mock_path.exists.return_value = True
        mock_path.name = "calculate_complexity.py"
        with patch("subprocess.run", side_effect=side_effect, return_value=run_result):
            with patch("lib.engine.hybrid.check_server_available", return_value=False):
                result = run(tmp_path, "python")

    warnings = [line for line in capsys.readouterr().err.splitlines() if line.startswith("[WARN]")]
    assert warnings == [f"[WARN] KISS: calculate_complexity.py failed: {expected}"]
    assert result["success"] is True
    assert result["violations"] == []
