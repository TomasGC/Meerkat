"""Unit tests for checkers/check_slap.py — local AI mocked via check_server_available / analyze_files_parallel.

check_slap.run() keeps its own check_server_available guard (hard-fails when
the AI server is down), then delegates to lib.engine.hybrid.run_hybrid(). The
guard is patched on the checker module; the AI pass itself (run_hybrid's own
availability gate + analyze_files_parallel + file discovery) is exercised
through lib.engine.hybrid, since that's where the real call sites live.
"""

from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from cca.checkers.check_slap import run

_CHECK_AVAILABLE = "cca.checkers.check_slap.check_server_available"
_HYBRID_CHECK_AVAILABLE = "lib.engine.hybrid.check_server_available"
_HYBRID_ANALYZE_PARALLEL = "lib.engine.hybrid.analyze_files_parallel"


# ── Local AI unavailable ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_server_unavailable_returns_failure(tmp_path):
    """Local AI not available → success: False, violations: [] (checker's own guard)."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")
    assert result["success"] is False
    assert result["violations"] == []
    assert result["principle"] == "SLAP"


# ── Violation returned ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_violation_mapped_with_principle(tmp_path):
    """Local AI returns SLAP violation → mapped with principle: SLAP."""
    f = tmp_path / "handler.py"
    f.write_text(
        "def process_order(order):\n"
        "    db.connect()\n"
        "    order.validate()\n"
        "    result = db.query('SELECT ...')\n"
        "    return result\n"
    )

    raw_item = {
        "source_file": str(f),
        "source_file_name": f.name,
        "function": "process_order",
        "violation": "Mixes high-level business logic with low-level DB calls",
        "severity": "medium",
        "suggestion": "Extract low-level operations into separate helper functions",
        "line": 1,
    }
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_ANALYZE_PARALLEL, return_value=[raw_item]):
        result = run(tmp_path, "python", files=[f])

    assert result["success"] is True
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["principle"] == "SLAP"
    assert "process_order" in v["message"]
    assert v["severity"] == "medium"


# ── Empty response ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_empty_response_no_violations(tmp_path):
    """Local AI returns [] → success: True, violations: []."""
    f = tmp_path / "clean.py"
    f.write_text("def greet(name): return f'Hello {name}'\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]):
        result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    assert result["violations"] == []


# ── files= parameter ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_files_none_discovers_all(tmp_path):
    """files=None → real file discovery finds the file (discovery path used)."""
    f = tmp_path / "svc.py"
    f.write_text("def fn(): pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]) as mock_analyze:
        result = run(tmp_path, "python", files=None)
    assert result["success"] is True
    called_files = mock_analyze.call_args[0][0]
    assert f in called_files


@pytest.mark.unit
def test_slap_files_provided_skips_discovery(tmp_path):
    """files=[path] → only the provided file is analyzed; other files on disk are ignored."""
    f = tmp_path / "svc.py"
    f.write_text("def fn(): pass\n")
    other = tmp_path / "other.py"
    other.write_text("def other_fn(): pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]) as mock_analyze:
        result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    called_files = mock_analyze.call_args[0][0]
    assert f in called_files
    assert other not in called_files


# ── Chunking (verify analyze_files_parallel is called for large files) ──────────

@pytest.mark.unit
def test_slap_large_file_passed_to_analyze(tmp_path):
    """Large file → analyze_files_parallel called with that file."""
    large_file = tmp_path / "big_handler.py"
    large_file.write_text("def fn():\n    pass\n" + "# padding\n" * 1000)

    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_CHECK_AVAILABLE, return_value=True), \
         patch(_HYBRID_ANALYZE_PARALLEL, return_value=[]) as mock_analyze:
        run(tmp_path, "python", files=[large_file], no_cache=True)

    mock_analyze.assert_called_once()
    call_files = mock_analyze.call_args[0][0]
    assert large_file in call_files
