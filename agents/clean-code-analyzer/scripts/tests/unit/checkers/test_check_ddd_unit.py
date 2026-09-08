"""Unit tests for checkers/check_ddd.py — local AI mocked via check_server_available / analyze_files_parallel."""

from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from checkers.check_ddd import run
    _DDD_AVAILABLE = True
except ImportError:
    _DDD_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _DDD_AVAILABLE, reason="check_ddd not importable"
)


# ── Local AI unavailable ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_server_unavailable_returns_failure(tmp_path):
    """Local AI not available → success: False, violations: []."""
    with patch("checkers.check_ddd.check_server_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["success"] is False
    assert result["violations"] == []
    assert result["principle"] == "DDD"


# ── Violation returned ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_anemic_model_violation_mapped(tmp_path):
    """Local AI returns anemic domain model violation → mapped with principle: DDD."""
    f = tmp_path / "user.py"
    f.write_text("class User:\n    name: str\n    email: str\n")

    raw_item = {
        "source_file": str(f),
        "source_file_name": f.name,
        "pattern": "AnemicDomainModel",
        "class_or_method": "User",
        "violation": "No behavior methods — pure data bag",
        "severity": "high",
        "suggestion": "Move domain logic into the entity",
        "line": 1,
    }
    with patch("checkers.check_ddd.check_server_available", return_value=True):
        with patch("checkers.check_ddd.analyze_files_parallel", return_value=[raw_item]):
            result = run(tmp_path, "python", files=[f])

    assert result["success"] is True
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["principle"] == "DDD"
    assert "AnemicDomainModel" in v["message"]
    assert v["severity"] == "high"


# ── Empty response ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_empty_response_no_violations(tmp_path):
    """Local AI returns [] → success: True, violations: []."""
    f = tmp_path / "good.py"
    f.write_text("class Order:\n    def place(self): pass\n")
    with patch("checkers.check_ddd.check_server_available", return_value=True):
        with patch("checkers.check_ddd.analyze_files_parallel", return_value=[]):
            result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    assert result["violations"] == []


# ── files= parameter ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_files_none_discovers_all(tmp_path):
    """files=None → discover_files is used (mocked to return a single file)."""
    f = tmp_path / "model.py"
    f.write_text("class Foo: pass\n")
    with patch("checkers.check_ddd.check_server_available", return_value=True):
        with patch("checkers.check_ddd.discover_files", return_value=[f]) as mock_discover:
            with patch("checkers.check_ddd.analyze_files_parallel", return_value=[]):
                result = run(tmp_path, "python", files=None)
    assert result["success"] is True
    mock_discover.assert_called_once()


@pytest.mark.unit
def test_ddd_files_provided_skips_discovery(tmp_path):
    """files=[path] → discover_files NOT called; provided list used directly."""
    f = tmp_path / "model.py"
    f.write_text("class Foo: pass\n")
    with patch("checkers.check_ddd.check_server_available", return_value=True):
        with patch("checkers.check_ddd.discover_files") as mock_discover:
            with patch("checkers.check_ddd.analyze_files_parallel", return_value=[]):
                result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    mock_discover.assert_not_called()


# ── Chunking (verify analyze_files_parallel is called for large files) ──────────

@pytest.mark.unit
def test_ddd_large_file_passed_to_analyze(tmp_path):
    """Large file → analyze_files_parallel called with that file."""
    large_file = tmp_path / "big_model.py"
    large_file.write_text("class Big:\n    pass\n" + "# padding\n" * 1000)

    with patch("checkers.check_ddd.check_server_available", return_value=True):
        with patch("checkers.check_ddd.analyze_files_parallel", return_value=[]) as mock_analyze:
            run(tmp_path, "python", files=[large_file], no_cache=True)

    mock_analyze.assert_called_once()
    call_files = mock_analyze.call_args[0][0]
    assert large_file in call_files
