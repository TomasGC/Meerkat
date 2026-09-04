"""Unit tests for checkers/check_dry.py — mocks subprocess and _FIND_DUPLICATES."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import checkers.check_dry as dry_mod
from checkers.check_dry import run

FIND_DUPLICATES_OUTPUT = json.dumps({
    "success": True,
    "files_analyzed": 2,
    "duplicates": [
        {
            "locations": [
                {"file": "a.py", "lines": "10-15"},
                {"file": "b.py", "lines": "5-10"},
            ],
            "similarity": 0.95,
            "lines": 6,
            "severity": "high",
        }
    ],
})


@pytest.mark.unit
def test_dry_maps_output(tmp_path):
    """DRY run maps find_duplicates.py JSON output to violations list."""
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path, \
         patch("subprocess.run") as mock_run:
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=FIND_DUPLICATES_OUTPUT,
            stderr="",
        )
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["principle"] == "DRY"
    assert len(result["violations"]) == 1
    assert result["violations"][0]["severity"] == "high"
    assert "DRY" in result["violations"][0]["principle"]


@pytest.mark.unit
def test_dry_subprocess_failure(tmp_path):
    """Non-zero returncode → success=False, violations=[]."""
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path, \
         patch("subprocess.run") as mock_run:
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []


@pytest.mark.unit
def test_dry_find_duplicates_missing(tmp_path):
    """When find_duplicates.py does not exist → success=False."""
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path:
        mock_path.exists.return_value = False
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []


@pytest.mark.unit
def test_dry_no_duplicates(tmp_path):
    """Empty duplicates list → 0 violations, success=True."""
    output = json.dumps({"success": True, "files_analyzed": 1, "duplicates": []})
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path, \
         patch("subprocess.run") as mock_run:
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


# ── error paths ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_dry_timeout_returns_failure(tmp_path):
    """subprocess.TimeoutExpired → success=False, violations=[]."""
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path, \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired("python", 60)):
        mock_path.exists.return_value = True
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []


@pytest.mark.unit
def test_dry_json_decode_error_returns_failure(tmp_path):
    """Malformed JSON from find_duplicates.py → success=False, violations=[]."""
    with patch.object(dry_mod, "_FIND_DUPLICATES") as mock_path, \
         patch("subprocess.run") as mock_run:
        mock_path.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="not valid json {{{", stderr="")
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []
