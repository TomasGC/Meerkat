"""Unit tests for checkers/check_ddd.py — Ollama mocked via analyze_files_parallel."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
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


# ── Ollama unavailable ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_ollama_unavailable_returns_failure(tmp_path):
    """Ollama model not available → success: False, violations: []."""
    with patch("checkers.check_ddd.check_ollama_available", return_value=False):
        result = run(tmp_path, "python")
    assert result["success"] is False
    assert result["violations"] == []
    assert result["principle"] == "DDD"


# ── Violation returned ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_anemic_model_violation_mapped(tmp_path):
    """Ollama returns anemic domain model violation → mapped with principle: DDD."""
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
    with patch("checkers.check_ddd.check_ollama_available", return_value=True):
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
    """Ollama returns [] → success: True, violations: []."""
    f = tmp_path / "good.py"
    f.write_text("class Order:\n    def place(self): pass\n")
    with patch("checkers.check_ddd.check_ollama_available", return_value=True):
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
    with patch("checkers.check_ddd.check_ollama_available", return_value=True):
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
    with patch("checkers.check_ddd.check_ollama_available", return_value=True):
        with patch("checkers.check_ddd.discover_files") as mock_discover:
            with patch("checkers.check_ddd.analyze_files_parallel", return_value=[]):
                result = run(tmp_path, "python", files=[f])
    assert result["success"] is True
    mock_discover.assert_not_called()


# ── Chunking ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_ddd_large_file_split_into_chunks(tmp_path):
    """File >8000 chars → split into multiple chunks, one Ollama call per chunk."""
    large_file = tmp_path / "big_model.py"
    large_file.write_text("class Big:\n    pass\n" + "# padding\n" * 1000)

    prompts_dir = tmp_path / "ollama_prompts"
    prompts_dir.mkdir()
    (prompts_dir / "ddd_analysis.prompt").write_text("Analyze {language}:\n{source}")

    import common.ollama_utils as ou
    original_dir = ou._PROMPTS_DIR
    ou._PROMPTS_DIR = prompts_dir
    mock_ollama = AsyncMock(return_value="[]")
    try:
        with patch("checkers.check_ddd.check_ollama_available", return_value=True):
            with patch("common.ollama_utils.call_ollama_async", mock_ollama):
                run(tmp_path, "python", files=[large_file], no_cache=True)
    finally:
        ou._PROMPTS_DIR = original_dir

    # File ~10 020 chars → at least 2 chunks, no truncation marker
    prompts = [call.args[0] for call in mock_ollama.call_args_list]
    assert len(prompts) >= 2
    assert not any("// ... (truncated)" in p for p in prompts)
