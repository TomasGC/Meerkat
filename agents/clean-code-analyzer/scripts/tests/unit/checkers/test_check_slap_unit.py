"""Unit tests for checkers/check_slap.py — Ollama mocked via analyze_files_parallel."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from checkers.check_slap import run
    _SLAP_AVAILABLE = True
except ImportError:
    _SLAP_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _SLAP_AVAILABLE, reason="check_slap not importable"
)


# ── Ollama unavailable ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_ollama_unavailable_returns_failure(tmp_path):
    """Ollama model not available → success: False, violations: []."""
    with patch("checkers.check_slap.check_ollama_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["success"] is False
    assert result["violations"] == []
    assert result["principle"] == "SLAP"


# ── Violation returned ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_violation_mapped_with_principle(tmp_path):
    """Ollama returns SLAP violation → mapped with principle: SLAP."""
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
    with patch("checkers.check_slap.check_ollama_available", return_value=True):
        with patch("checkers.check_slap.analyze_files_parallel", return_value=[raw_item]):
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
    """Ollama returns [] → success: True, violations: []."""
    f = tmp_path / "clean.py"
    f.write_text("def greet(name): return f'Hello {name}'\n")
    with patch("checkers.check_slap.check_ollama_available", return_value=True):
        with patch("checkers.check_slap.analyze_files_parallel", return_value=[]):
            result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    assert result["violations"] == []


# ── files= parameter ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_files_none_discovers_all(tmp_path):
    """files=None → discover_files is called (discovery path used)."""
    f = tmp_path / "svc.py"
    f.write_text("def fn(): pass\n")
    with patch("checkers.check_slap.check_ollama_available", return_value=True):
        with patch("checkers.check_slap.discover_files", return_value=[f]) as mock_discover:
            with patch("checkers.check_slap.analyze_files_parallel", return_value=[]):
                result = run(tmp_path, "python", files=None)
    assert result["success"] is True
    mock_discover.assert_called_once()


@pytest.mark.unit
def test_slap_files_provided_skips_discovery(tmp_path):
    """files=[path] → discover_files NOT called."""
    f = tmp_path / "svc.py"
    f.write_text("def fn(): pass\n")
    with patch("checkers.check_slap.check_ollama_available", return_value=True):
        with patch("checkers.check_slap.discover_files") as mock_discover:
            with patch("checkers.check_slap.analyze_files_parallel", return_value=[]):
                result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    mock_discover.assert_not_called()


# ── Chunking ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_slap_large_file_split_into_chunks(tmp_path):
    """File >8000 chars → split into multiple chunks, one Ollama call per chunk."""
    large_file = tmp_path / "big_handler.py"
    large_file.write_text("def fn():\n    pass\n" + "# padding\n" * 1000)

    prompts_dir = tmp_path / "ollama_prompts"
    prompts_dir.mkdir()
    (prompts_dir / "slap_analysis.prompt").write_text("Analyze {language}:\n{source}")

    import common.ollama_utils as ou
    original_dir = ou._PROMPTS_DIR
    ou._PROMPTS_DIR = prompts_dir
    mock_ollama = AsyncMock(return_value="[]")
    try:
        with patch("checkers.check_slap.check_ollama_available", return_value=True):
            with patch("common.ollama_utils.call_ollama_async", mock_ollama):
                run(tmp_path, "python", files=[large_file], no_cache=True)
    finally:
        ou._PROMPTS_DIR = original_dir

    # File ~10 019 chars → at least 2 chunks, no truncation marker
    prompts = [call.args[0] for call in mock_ollama.call_args_list]
    assert len(prompts) >= 2
    assert not any("// ... (truncated)" in p for p in prompts)
