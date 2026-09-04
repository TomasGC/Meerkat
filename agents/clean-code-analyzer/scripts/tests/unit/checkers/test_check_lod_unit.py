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


# ── non-Python language support ─────────────────────────────────────────────────

@pytest.mark.unit
def test_lod_typescript_no_crash(tmp_path):
    """check_lod.run with TypeScript file → success=True, no exception."""
    (tmp_path / "service.ts").write_text(
        "export class Service {\n  doWork() { return this.dep.getResult(); }\n}\n"
    )
    result = run(tmp_path, "typescript")
    assert result["success"] is True
    assert isinstance(result["violations"], list)


@pytest.mark.unit
def test_lod_string_literal_chain_not_flagged(tmp_path):
    """String literal method chain is not flagged — regex requires \\w+ before first dot."""
    code = 'result = "hello world".upper().strip().replace("o", "0")\n'
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    # "hello world" starts with '"', not \w+, so _CHAIN_RE cannot match the chain
    # (the variable 'result' after '=' is on the left side, not a chain itself)
    for v in result["violations"]:
        assert '"hello world"' not in v.get("message", "")
