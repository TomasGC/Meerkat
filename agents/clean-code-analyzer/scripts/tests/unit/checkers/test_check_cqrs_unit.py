"""Unit tests for checkers/check_cqrs.py — mocks Ollama calls.

Pattern mirrors test_check_solid_unit.py: patch check_ollama_available
and analyze_files_parallel as bound names in the checker module.
"""

from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import checkers.check_cqrs as cqrs_mod
    from checkers.check_cqrs import run
    _CQRS_AVAILABLE = True
except ImportError:
    _CQRS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _CQRS_AVAILABLE, reason="check_cqrs not implemented yet")

_CHECK_AVAILABLE = "checkers.check_cqrs.check_ollama_available"
_ANALYZE_PARALLEL = "checkers.check_cqrs.analyze_files_parallel"


@pytest.mark.unit
def test_cqrs_returns_violations_when_ollama_available(tmp_path):
    """CQRS checker maps Ollama items to violations."""
    (tmp_path / "app.py").write_text(
        "class OrderService:\n"
        "    def save_and_get(self, order): pass\n"
    )
    mock_items = [
        {
            "source_file": str(tmp_path / "app.py"),
            "line": 2,
            "severity": "high",
            "violation": "Command and query mixed in one method",
            "suggestion": "Separate into save() and get() methods",
        }
    ]
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=mock_items):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1


@pytest.mark.unit
def test_cqrs_empty_when_no_violations(tmp_path):
    """Empty response → 0 violations, success=True."""
    (tmp_path / "app.py").write_text("class QueryService: pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=[]):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_cqrs_failure_when_ollama_unavailable(tmp_path):
    """Ollama not available → success=False, violations=[]."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []


@pytest.mark.unit
def test_cqrs_return_schema(tmp_path):
    """Return dict has all required keys."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert "principle" in result
    assert "success" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)
