"""Tests for check_inheritance — Composition over Inheritance detection."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from checkers.check_inheritance import _check_python


@pytest.mark.parametrize("code,should_flag", [
    # Deep inheritance chain (depth 4) — SHOULD flag
    (
        "class A: pass\n"
        "class B(A): pass\n"
        "class C(B): pass\n"
        "class D(C): pass\n"
        "class E(D): pass\n",
        True,
    ),
    # Shallow single inheritance — should NOT flag
    ("class Animal: pass\nclass Dog(Animal): pass\n", False),
    # No inheritance — should NOT flag
    ("class Service:\n    def process(self): pass\n", False),
    # Multiple non-interface inheritance — SHOULD flag
    ("class A: pass\nclass B: pass\nclass C(A, B): pass\n", True),
    # Mixin (interface marker) — should NOT flag
    ("class LogMixin: pass\nclass Service(LogMixin): pass\n", False),
    # Depth exactly 3 — should NOT flag (threshold is > 3)
    (
        "class A: pass\n"
        "class B(A): pass\n"
        "class C(B): pass\n"
        "class D(C): pass\n",
        False,
    ),
])
def test_inheritance_parametrized(tmp_path, code, should_flag):
    f = tmp_path / "module.py"
    f.write_text(code)
    violations = _check_python([f], tmp_path)
    has_violations = len(violations) > 0
    assert has_violations == should_flag, (
        f"Code:\n{code!r}\nExpected violations={should_flag}, got {violations}"
    )


class TestRunSignature:
    def test_accepts_files_param(self, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("class Foo: pass\n")
        from checkers.check_inheritance import run
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
        assert result["files_analyzed"] == 1

    def test_empty_file_no_violations(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        from checkers.check_inheritance import run
        result = run(tmp_path, "python", files=[f])
        assert result["violations"] == []
