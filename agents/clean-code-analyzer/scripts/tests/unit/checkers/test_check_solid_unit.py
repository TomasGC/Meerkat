"""Unit tests for checkers/check_solid.py — mocks Ollama calls."""

from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import checkers.check_solid as solid_mod
from checkers.check_solid import run

# Patch targets: check_solid imports these with 'from', so we patch the bound names.
_CHECK_AVAILABLE = "checkers.check_solid.check_ollama_available"
_ANALYZE_PARALLEL = "checkers.check_solid.analyze_files_parallel"


@pytest.mark.unit
def test_solid_returns_violations_when_ollama_available(tmp_path):
    """SOLID checker maps Ollama items to SOLID:X violations."""
    (tmp_path / "app.py").write_text(
        "class GodClass:\n"
        "    def a(self): pass\n"
        "    def b(self): pass\n"
    )
    mock_items = [
        {
            "source_file": str(tmp_path / "app.py"),
            "principle": "S",
            "line": 1,
            "severity": "high",
            "violation": "Too many responsibilities",
            "suggestion": "Split class",
        }
    ]
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=mock_items):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert len(result["violations"]) == 1
    assert result["violations"][0]["principle"].startswith("SOLID:")


@pytest.mark.unit
def test_solid_empty_violations_when_no_issues(tmp_path):
    """Empty Ollama response → 0 violations, success=True."""
    (tmp_path / "app.py").write_text("class Service: pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=[]):
        result = run(tmp_path, "python")

    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_solid_failure_when_ollama_unavailable(tmp_path):
    """Ollama not available → success=False, violations=[]."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert result["success"] is False
    assert result["violations"] == []
    assert "error" in result


@pytest.mark.unit
def test_solid_return_schema(tmp_path):
    """Return dict has all required keys."""
    with patch(_CHECK_AVAILABLE, return_value=False):
        result = run(tmp_path, "python")

    assert result["principle"] == "SOLID"
    assert "success" in result
    assert "violations" in result
    assert "files_analyzed" in result
    assert "duration_ms" in result


# ── files param + model override ────────────────────────────────────────────────

@pytest.mark.unit
def test_solid_files_param_skips_discovery(tmp_path):
    """When files param provided, only those files are analyzed (no discovery)."""
    explicit = tmp_path / "explicit.py"
    explicit.write_text("class X: pass\n")
    other = tmp_path / "other.py"
    other.write_text("class Y: pass\n")

    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=[]) as mock_analyze:
        run(tmp_path, "python", files=[explicit])

    called_files = mock_analyze.call_args[0][0]
    assert explicit in called_files
    assert other not in called_files


@pytest.mark.unit
def test_solid_model_override_propagated(tmp_path):
    """model param overrides _MODEL default and is passed to analyze_files_parallel."""
    (tmp_path / "app.py").write_text("class X: pass\n")
    with patch(_CHECK_AVAILABLE, return_value=True), \
         patch(_ANALYZE_PARALLEL, return_value=[]) as mock_analyze:
        run(tmp_path, "python", model="custom-model:latest")

    called_model = mock_analyze.call_args[0][2]  # positional: files, language, model, prompt
    assert called_model == "custom-model:latest"
