"""Unit tests for checkers/check_lod.py — regex/grep, no Ollama."""

from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from checkers.check_lod import run


@pytest.mark.unit
@pytest.mark.parametrize("code,should_flag", [
    # Three-level property chain (4 parts) → flag
    ("result = obj.service.repository.find_by_id(42)\n", True),
    # Triple method chain → flag
    ("val = a.get_b().get_c().get_d()\n", True),
    # Single-level property → no flag
    ("name = user.profile\n", False),
    # Two-level property chain — 3 parts, 2 dots → no flag (needs 3+ dots)
    ("name = user.profile.name\n", False),
    # Fluent query builder — exempt pattern
    ("items = db.query(User).filter(User.active).all()\n", False),
])
def test_lod(tmp_path, code, should_flag):
    """Parametrized Law of Demeter violation check."""
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    has_violations = len(result["violations"]) > 0
    assert has_violations == should_flag, (
        f"Code: {code!r}\n"
        f"Expected should_flag={should_flag}, "
        f"got violations={result['violations']}"
    )


@pytest.mark.unit
def test_lod_return_schema(tmp_path):
    """Return dict has required keys with correct principle name."""
    (tmp_path / "mod.py").write_text("x = 1\n")
    result = run(tmp_path, "python")
    assert result["principle"] == "LawOfDemeter"
    assert "success" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)
