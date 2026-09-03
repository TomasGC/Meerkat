"""Unit tests for checkers/check_naming.py — pure regex/grep, no Ollama."""

from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common.file_utils as fu
from checkers.check_naming import run as run_naming


@pytest.fixture(autouse=True)
def clear_cache():
    fu._DISCOVERY_CACHE.clear()
    yield
    fu._DISCOVERY_CACHE.clear()


@pytest.mark.unit
@pytest.mark.parametrize("code,expected_violations", [
    # Magic number in condition → flag
    ("if retries > 3600:\n    pass\n", 1),
    # Named constant (ALL_CAPS) definition → magic number NOT flagged
    ("MAX_RETRIES = 3600\nif retries > MAX_RETRIES:\n    pass\n", 0),
    # Loop variable (single letter) → do NOT flag (iterable var, no magic number)
    ("for i in items:\n    print(i)\n", 0),
    # Single-letter variable outside loop (not x/y/z) → flag
    ("a = compute_total()\nreturn a\n", 1),
    # Function param named 'id' (2 letters, no assignment) → do NOT flag
    ("def get_user(id):\n    pass\n", 0),
    # Magic string in equality condition → flag
    ('if status == "active":\n    pass\n', 1),
    # Common HTTP status code → do NOT flag
    ("if code == 404:\n    pass\n", 0),
])
def test_naming(tmp_path, code, expected_violations):
    """Parametrized naming violations check."""
    (tmp_path / "mod.py").write_text(code)
    result = run_naming(tmp_path, "python")
    assert result["success"] is True
    count = len(result["violations"])
    assert count == expected_violations, (
        f"Code: {code!r}\nExpected {expected_violations} violations, "
        f"got {count}: {result['violations']}"
    )
