"""Unit tests for checkers/check_inheritance.py — AST-based, no Ollama.

Threshold: depth > 3 means a 5-class chain (GoldenRetriever with depth 4)
is flagged, but a 4-class chain (depth 3) is NOT.
"""

from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from checkers.check_inheritance import run


@pytest.mark.unit
@pytest.mark.parametrize("code,should_flag", [
    # 5-class chain: GoldenRetriever depth=4 (> 3) → flag
    (
        "class A: pass\nclass B(A): pass\nclass C(B): pass\n"
        "class D(C): pass\nclass E(D): pass\n",
        True,
    ),
    # 2-class chain: depth=1 → no flag
    ("class Animal: pass\nclass Dog(Animal): pass\n", False),
    # No inheritance: depth=0 → no flag
    ("class Service:\n    def process(self): pass\n", False),
    # 3-class chain: depth=2 → no flag
    ("class A: pass\nclass B(A): pass\nclass C(B): pass\n", False),
    # 4-class chain: depth=3 (NOT > 3) → no flag
    ("class A: pass\nclass B(A): pass\nclass C(B): pass\nclass D(C): pass\n", False),
])
def test_inheritance(tmp_path, code, should_flag):
    """Parametrized composition-over-inheritance depth check."""
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
def test_inheritance_return_schema(tmp_path):
    """Return dict uses 'CompositionOverInheritance' principle name."""
    (tmp_path / "mod.py").write_text("class Foo: pass\n")
    result = run(tmp_path, "python")
    assert result["principle"] == "CompositionOverInheritance"
    assert "success" in result
    assert isinstance(result["violations"], list)
