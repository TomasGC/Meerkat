"""Unit tests for checkers/check_comments.py — regex/grep, no Ollama."""

from pathlib import Path
from unittest.mock import patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from checkers.check_comments import run
    _COMMENTS_AVAILABLE = True
except ImportError:
    _COMMENTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _COMMENTS_AVAILABLE, reason="check_comments not implemented yet"
)


@pytest.mark.unit
def test_comments_detects_todo(tmp_path):
    """TODO comments should be flagged."""
    (tmp_path / "mod.py").write_text("# TODO: fix this\nx = 1\n")
    result = run(tmp_path, "python")
    assert result["success"] is True
    assert len(result["violations"]) > 0


@pytest.mark.unit
def test_comments_clean_code_no_violations(tmp_path):
    """Clean code without TODO/FIXME → 0 violations."""
    code = (
        "SECONDS_PER_DAY = 86400\n\n"
        "def double(x):\n"
        "    return x * 2\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    assert result["violations"] == []


@pytest.mark.unit
def test_comments_return_schema(tmp_path):
    """Return dict has required keys."""
    (tmp_path / "mod.py").write_text("x = 1\n")
    result = run(tmp_path, "python")
    assert "principle" in result
    assert "success" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)


# ── Parametrized TODO/FIXME/HACK detection ─────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("line,expected_flag", [
    ("# TODO: fix this\n", True),
    ("# FIXME: broken\n", True),
    ("# HACK: workaround\n", True),
    ("# Regular comment explaining why this algorithm is used\n", False),
])
def test_comments_flagged_tags_parametrized(tmp_path, line, expected_flag):
    """TODO/FIXME/HACK are flagged; plain explanatory comments are not."""
    (tmp_path / "mod.py").write_text(line + "x = 1\n")
    result = run(tmp_path, "python")
    assert result["success"] is True
    violations = [v for v in result["violations"] if v.get("message", "").endswith("should be a tracked issue")]
    has_violation = len(violations) > 0
    assert has_violation == expected_flag, (
        f"Line: {line!r}, expected_flag={expected_flag}, violations={result['violations']}"
    )


# ── Dead code block detection ───────────────────────────────────────────────────

@pytest.mark.unit
def test_comments_two_consecutive_code_lines_flagged(tmp_path):
    """Two consecutive commented-out code lines → flagged as dead code block."""
    code = (
        "# def old_func():\n"
        "# return None\n"
        "x = 1\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    dead_code = [v for v in result["violations"] if "Commented-out code" in v.get("message", "")]
    assert len(dead_code) >= 1


@pytest.mark.unit
def test_comments_single_code_line_not_flagged(tmp_path):
    """Single commented-out code line alone → NOT flagged (threshold is ≥2)."""
    code = (
        "# def old_func():\n"
        "x = 1\n"  # non-code line resets the counter
        "y = 2\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    dead_code = [v for v in result["violations"] if "Commented-out code" in v.get("message", "")]
    assert len(dead_code) == 0


# ── Explain-WHAT comment detection ─────────────────────────────────────────────

@pytest.mark.unit
def test_comments_what_verb_flagged(tmp_path):
    """Comment that explains WHAT (e.g. '# increment counter') is flagged."""
    code = (
        "# increment counter\n"
        "counter += 1\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    what_violations = [v for v in result["violations"] if "WHAT" in v.get("message", "")]
    assert len(what_violations) >= 1
