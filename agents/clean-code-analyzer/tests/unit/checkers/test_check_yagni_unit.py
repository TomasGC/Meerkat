"""Unit tests for checkers/check_yagni.py — subprocess and local AI mocked.

check_yagni.run() delegates to lib.engine.hybrid.run_hybrid() with a
mechanical_fn that shells out to find_unused_code.py. The mechanical
subprocess call still lives on the checker module (_FIND_UNUSED,
subprocess.run), so those patch targets are unchanged. The AI pass
(availability guard + analyze_files_parallel) now lives inside run_hybrid,
so those are patched on lib.engine.hybrid, where the real call sites are.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cca.checkers.check_yagni import run

_HYBRID_CHECK_AVAILABLE = "lib.engine.hybrid.check_server_available"
_HYBRID_ANALYZE_PARALLEL = "lib.engine.hybrid.analyze_files_parallel"


# ── Subprocess path ─────────────────────────────────────────────────────────────


def _symbol(file: str, name: str, line_start: int, line_end: int | None = None) -> dict:
    """One entry of find_unused_code.py's `unused_symbols`, in the exact shape the script emits."""
    return {
        "file": file,
        "type": "function",
        "name": name,
        "line_start": line_start,
        "line_end": line_end if line_end is not None else line_start + 1,
        "confidence": "high",
    }


def _unused_payload(*symbols: dict) -> str:
    """find_unused_code.py --format json stdout. The script emits no `files_analyzed` key."""
    return json.dumps(
        {
            "success": True,
            "language": "python",
            "path": "/fake/project",
            "total_unused": len(symbols),
            "unused_symbols": list(symbols),
        }
    )


_UNUSED_JSON = _unused_payload(_symbol("src/utils.py", "old_helper", 10))

_UNUSED_TWO_FILES_JSON = _unused_payload(
    _symbol("targeted.py", "targeted_func", 5),
    _symbol("other.py", "other_func", 8),
)


def _run_with_unused(tmp_path: Path, stdout: str, ai_items: list[dict] | None = None, files=None) -> dict:
    """Run the checker with find_unused_code.py mocked to `stdout`; AI pass on iff ai_items is given."""
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=stdout)):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=ai_items is not None):
                with patch(_HYBRID_ANALYZE_PARALLEL, return_value=ai_items or []):
                    return run(tmp_path, "python", files=files)


def test_subprocess_unused_code_mapped_to_yagni(tmp_path):
    """Subprocess returns unused code JSON → violation with principle: YAGNI."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["principle"] == "YAGNI"
    assert "old_helper" in v["message"]
    assert v["severity"] == "high"
    assert v["line"] == 10  # the script's line_start, not a defaulted 0


def test_two_unused_symbols_same_file_stay_two_findings(tmp_path):
    """Two unused symbols in one file at different lines → two findings, each at its own line."""
    stdout = _unused_payload(
        _symbol("app.py", "first_unused", 3),
        _symbol("app.py", "second_unused", 12),
    )

    result = _run_with_unused(tmp_path, stdout)

    assert result["success"] is True
    assert sorted((v["file"], v["line"]) for v in result["violations"]) == [("app.py", 3), ("app.py", 12)]


def test_subprocess_failure_empty_violations(tmp_path):
    """subprocess raises OSError → violations empty, success True, no exception raised."""
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", side_effect=OSError("not found")):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


def test_subprocess_timeout_empty_violations(tmp_path):
    """subprocess.TimeoutExpired → violations empty, success True."""
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


# ── Ollama path ─────────────────────────────────────────────────────────────────


def test_ollama_speculative_violation_added(tmp_path):
    """Ollama returns speculative feature violation → added to results with principle YAGNI.

    _FIND_UNUSED.exists()=False skips the mechanical layer entirely, so there is
    no mechanical finding for this AI finding to reconcile against — this test is
    about the AI layer surfacing a violation on its own.
    """
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    def get_user(self): pass\n")

    ollama_item = {
        "source_file": str(f),
        "source_file_name": f.name,
        "pattern": "SpeculativeGenerality",
        "violation": "Method never called",
        "severity": "medium",
        "suggestion": "Remove if unused",
        "line": 2,
    }
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = False  # skip subprocess
        with patch(_HYBRID_CHECK_AVAILABLE, return_value=True):
            with patch(_HYBRID_ANALYZE_PARALLEL, return_value=[ollama_item]):
                result = run(tmp_path, "python", files=[f])

    assert result["success"] is True
    yagni_v = [v for v in result["violations"] if v["principle"] == "YAGNI"]
    assert len(yagni_v) == 1
    assert "SpeculativeGenerality" in yagni_v[0]["message"]


def test_ollama_unavailable_subprocess_results_still_returned(tmp_path):
    """Ollama unavailable → Ollama part skipped, subprocess violations still returned."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1  # subprocess violation still present


# ── Incremental file filtering ──────────────────────────────────────────────────


def test_files_filter_only_targeted_file(tmp_path):
    """files=[targeted.py] → only violations for that file returned from subprocess."""
    targeted = tmp_path / "targeted.py"
    targeted.write_text("def targeted_func(): pass\n")

    mock_result = MagicMock(returncode=0, stdout=_UNUSED_TWO_FILES_JSON)
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python", files=[targeted])

    assert result["success"] is True
    # Only violations for targeted.py should be included (filter by filename)
    for v in result["violations"]:
        assert "targeted" in v["file"]


def test_files_none_runs_full_path(tmp_path):
    """files=None → analyzes full path (no file filtering)."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=False):
                result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    # All violations from subprocess returned (no filtering)
    assert len(result["violations"]) == 1


# ── Ollama with files=None hits discover_files branch ───────────────────────────


def test_yagni_ollama_discover_files_branch(tmp_path):
    """When files=None and Ollama available → default discovery branch is hit."""
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    def get_user(self): pass\n")

    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path, patch(
        _HYBRID_CHECK_AVAILABLE, return_value=True
    ), patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]) as mock_ollama:
        mock_path.exists.return_value = False
        result = run(tmp_path, "python", files=None)

    mock_ollama.assert_called_once()
    assert result["success"] is True


def test_yagni_ollama_discover_files_mixed_language(tmp_path):
    """language='mixed' → exts=None, discovery finds all supported files."""
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    pass\n")

    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path, patch(
        _HYBRID_CHECK_AVAILABLE, return_value=True
    ), patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]):
        mock_path.exists.return_value = False
        result = run(tmp_path, "mixed", files=None)

    assert result["success"] is True


# ── Reconciliation (mechanical + AI proximity dedup) ────────────────────────────


def test_ai_finding_near_mechanical_dropped(tmp_path):
    """AI finding within 3 lines of a mechanical finding in the same file is dropped as a near-duplicate."""
    f = tmp_path / "app.py"
    f.write_text("def old_helper(): pass\n" * 10)

    unused_json = _unused_payload(_symbol("app.py", "old_helper", 5))
    ollama_item = {
        "source_file": str(f),
        "pattern": "SpeculativeGenerality",
        "violation": "Duplicate of mechanical finding",
        "severity": "medium",
        "suggestion": "Remove if unused",
        "line": 6,  # within 3 lines of the mechanical finding's line_start=5
    }

    result = _run_with_unused(tmp_path, unused_json, ai_items=[ollama_item])

    assert result["success"] is True
    assert len(result["violations"]) == 1
    assert "old_helper" in result["violations"][0]["message"]
    assert result["violations"][0]["line"] == 5


def test_ai_finding_far_from_mechanical_both_kept(tmp_path):
    """AI finding more than 3 lines from a mechanical finding in the same file survives reconciliation."""
    f = tmp_path / "app.py"
    f.write_text("def old_helper(): pass\n" * 20)

    unused_json = _unused_payload(_symbol("app.py", "old_helper", 5))
    ollama_item = {
        "source_file": str(f),
        "pattern": "SpeculativeGenerality",
        "violation": "Unrelated speculative feature elsewhere in the file",
        "severity": "medium",
        "suggestion": "Remove if unused",
        "line": 18,  # far from the mechanical finding's line_start=5
    }

    result = _run_with_unused(tmp_path, unused_json, ai_items=[ollama_item])

    assert result["success"] is True
    assert len(result["violations"]) == 2
    messages = [v["message"] for v in result["violations"]]
    assert any("old_helper" in m for m in messages)
    assert any("SpeculativeGenerality" in m for m in messages)


@pytest.mark.parametrize(
    "returncode, stdout, reason",
    [
        (0, json.dumps({"success": False, "error": "Unsupported language: unknown"}), "Unsupported language: unknown"),
        (1, "", "exit code 1"),
    ],
)
def test_tool_failure_warns_on_stderr_and_still_runs_ai(tmp_path, capsys, returncode, stdout, reason):
    """find_unused_code.py failing is reported once on stderr; the AI pass still runs."""
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")
    ai_item = {
        "line": 1,
        "pattern": "speculative-feature",
        "violation": "v",
        "suggestion": "s",
        "source_file": str(tmp_path / "app.py"),
    }
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.name = "find_unused_code.py"
        with patch("subprocess.run", return_value=MagicMock(returncode=returncode, stdout=stdout, stderr="")):
            with patch(_HYBRID_CHECK_AVAILABLE, return_value=True):
                with patch(_HYBRID_ANALYZE_PARALLEL, return_value=[ai_item]):
                    result = run(tmp_path, "python")

    warnings = [line for line in capsys.readouterr().err.splitlines() if line.startswith("[WARN]")]
    assert warnings == [f"[WARN] YAGNI: find_unused_code.py failed: {reason}"]
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
    with patch("cca.checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.name = "find_unused_code.py"
        with patch("subprocess.run", side_effect=side_effect, return_value=run_result):
            with patch("lib.engine.hybrid.check_server_available", return_value=False):
                result = run(tmp_path, "python")

    warnings = [line for line in capsys.readouterr().err.splitlines() if line.startswith("[WARN]")]
    assert warnings == [f"[WARN] YAGNI: find_unused_code.py failed: {expected}"]
    assert result["success"] is True
    assert result["violations"] == []
