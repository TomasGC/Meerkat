"""Unit tests for checkers/check_yagni.py — subprocess and Ollama mocked."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from checkers.check_yagni import run
    _YAGNI_AVAILABLE = True
except ImportError:
    _YAGNI_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _YAGNI_AVAILABLE, reason="check_yagni not importable"
)


# ── Subprocess path ─────────────────────────────────────────────────────────────

_UNUSED_JSON = json.dumps({
    "files_analyzed": 3,
    "unused_symbols": [
        {"file": "src/utils.py", "line": 10, "type": "function", "name": "old_helper", "confidence": "high"},
    ],
})

_UNUSED_TWO_FILES_JSON = json.dumps({
    "files_analyzed": 2,
    "unused_symbols": [
        {"file": "targeted.py", "line": 5, "type": "function", "name": "targeted_func", "confidence": "high"},
        {"file": "other.py", "line": 8, "type": "function", "name": "other_func", "confidence": "high"},
    ],
})


@pytest.mark.unit
def test_subprocess_unused_code_mapped_to_yagni(tmp_path):
    """Subprocess returns unused code JSON → violation with principle: YAGNI."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["principle"] == "YAGNI"
    assert "old_helper" in v["message"]
    assert v["severity"] == "high"


@pytest.mark.unit
def test_subprocess_failure_empty_violations(tmp_path):
    """subprocess raises OSError → violations empty, success True, no exception raised."""
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", side_effect=OSError("not found")):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_subprocess_timeout_empty_violations(tmp_path):
    """subprocess.TimeoutExpired → violations empty, success True."""
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


# ── Ollama path ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ollama_speculative_violation_added(tmp_path):
    """Ollama returns speculative feature violation → added to results with principle YAGNI."""
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
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = False  # skip subprocess
        with patch("checkers.check_yagni.check_ollama_available", return_value=True):
            with patch("checkers.check_yagni.analyze_files_parallel", return_value=[ollama_item]):
                result = run(tmp_path, "python", files=[f])

    assert result["success"] is True
    yagni_v = [v for v in result["violations"] if v["principle"] == "YAGNI"]
    assert len(yagni_v) == 1
    assert "SpeculativeGenerality" in yagni_v[0]["message"]


@pytest.mark.unit
def test_ollama_unavailable_subprocess_results_still_returned(tmp_path):
    """Ollama unavailable → Ollama part skipped, subprocess violations still returned."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1  # subprocess violation still present


# ── Incremental file filtering ──────────────────────────────────────────────────

@pytest.mark.unit
def test_files_filter_only_targeted_file(tmp_path):
    """files=[targeted.py] → only violations for that file returned from subprocess."""
    targeted = tmp_path / "targeted.py"
    targeted.write_text("def targeted_func(): pass\n")

    mock_result = MagicMock(returncode=0, stdout=_UNUSED_TWO_FILES_JSON)
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python", files=[targeted])

    assert result["success"] is True
    # Only violations for targeted.py should be included (filter by filename)
    for v in result["violations"]:
        assert "targeted" in v["file"]


@pytest.mark.unit
def test_files_none_runs_full_path(tmp_path):
    """files=None → analyzes full path (no file filtering)."""
    mock_result = MagicMock(returncode=0, stdout=_UNUSED_JSON)
    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path:
        mock_path.exists.return_value = True
        mock_path.__str__.return_value = "/fake/find_unused.py"
        with patch("subprocess.run", return_value=mock_result):
            with patch("checkers.check_yagni.check_ollama_available", return_value=False):
                result = run(tmp_path, "python", files=None)

    assert result["success"] is True
    # All violations from subprocess returned (no filtering)
    assert len(result["violations"]) == 1


# ── Ollama with files=None hits discover_files branch ───────────────────────────

@pytest.mark.unit
def test_yagni_ollama_discover_files_branch(tmp_path):
    """When files=None and Ollama available → discover_files branch (lines 65-67) hit."""
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    def get_user(self): pass\n")

    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path, \
         patch("checkers.check_yagni.check_ollama_available", return_value=True), \
         patch("checkers.check_yagni.analyze_files_parallel", return_value=[]) as mock_ollama:
        mock_path.exists.return_value = False
        result = run(tmp_path, "python", files=None)

    mock_ollama.assert_called_once()
    assert result["success"] is True


@pytest.mark.unit
def test_yagni_ollama_discover_files_mixed_language(tmp_path):
    """language='mixed' → exts=None, discover_files finds all supported files."""
    f = tmp_path / "service.py"
    f.write_text("class UserService:\n    pass\n")

    with patch("checkers.check_yagni._FIND_UNUSED") as mock_path, \
         patch("checkers.check_yagni.check_ollama_available", return_value=True), \
         patch("checkers.check_yagni.analyze_files_parallel", return_value=[]):
        mock_path.exists.return_value = False
        result = run(tmp_path, "mixed", files=None)

    assert result["success"] is True
