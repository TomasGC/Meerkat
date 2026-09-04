"""Unit tests for checkers/check_inheritance.py — AST-based, no Ollama.

Threshold: depth > 3 means a 5-class chain (GoldenRetriever with depth 4)
is flagged, but a 4-class chain (depth 3) is NOT.
"""

from pathlib import Path
import sys
from unittest.mock import patch

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


# ── multiple inheritance ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_inheritance_multiple_non_interface_parents_flagged(tmp_path):
    """Multiple inheritance with two non-interface parents → violation."""
    code = (
        "class ConcreteA: pass\n"
        "class ConcreteB: pass\n"
        "class Combined(ConcreteA, ConcreteB): pass\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    multi = [v for v in result["violations"] if "multiple inheritance" in v["message"].lower()]
    assert len(multi) >= 1


@pytest.mark.unit
def test_inheritance_multiple_with_interface_not_flagged(tmp_path):
    """Multiple inheritance where one parent is IRepository (interface marker) → no violation."""
    code = (
        "class ServiceBase: pass\n"
        "class IRepository: pass\n"
        "class MyService(ServiceBase, IRepository): pass\n"
    )
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    multi = [v for v in result["violations"] if "multiple inheritance" in v["message"].lower()]
    assert len(multi) == 0


# ── error path ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_inheritance_oserror_skips_file(tmp_path):
    """OSError reading a Python file → file skipped gracefully, success=True."""
    (tmp_path / "mod.py").write_text("class A: pass\n")
    with patch("pathlib.Path.read_text", side_effect=OSError("permission denied")):
        result = run(tmp_path, "python")
    assert result["success"] is True
    assert result["violations"] == []


# ── circular guard ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_inheritance_circular_guard_no_recursion_error(tmp_path):
    """Circular class hierarchy does not cause infinite recursion."""
    from checkers.check_inheritance import _inheritance_depth
    parents_map = {"A": ["B"], "B": ["A"]}
    depth = _inheritance_depth("A", parents_map, set())
    assert isinstance(depth, int)
    assert depth >= 0


# ── non-Python (TypeScript) deep chain ─────────────────────────────────────────

@pytest.mark.unit
def test_inheritance_non_python_deep_chain_flagged(tmp_path):
    """TypeScript file with 5-class chain (depth 4 > 3) → violation."""
    code = (
        "class A {}\n"
        "class B extends A {}\n"
        "class C extends B {}\n"
        "class D extends C {}\n"
        "class E extends D {}\n"
    )
    (tmp_path / "Service.ts").write_text(code)
    result = run(tmp_path, "typescript")
    assert result["success"] is True
    assert len(result["violations"]) >= 1


@pytest.mark.unit
def test_inheritance_non_python_no_inheritance_no_violation(tmp_path):
    """TypeScript class with no inheritance → no violation."""
    code = "class SimpleService {\n  doWork() { return 1; }\n}\n"
    (tmp_path / "simple.ts").write_text(code)
    result = run(tmp_path, "typescript")
    assert result["success"] is True
    assert len(result["violations"]) == 0


# ── single file path ────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_inheritance_single_file_path(tmp_path):
    """run() with a single .py file (not directory) → files_analyzed=1."""
    f = tmp_path / "mod.py"
    f.write_text(
        "class A: pass\nclass B(A): pass\nclass C(B): pass\n"
        "class D(C): pass\nclass E(D): pass\n"
    )
    result = run(f, "python")
    assert result["success"] is True
    assert result["files_analyzed"] == 1
    assert len(result["violations"]) >= 1


@pytest.mark.unit
def test_inheritance_non_python_single_file_path(tmp_path):
    """run() with single non-.py file → uses other_files path (line 162)."""
    f = tmp_path / "Service.ts"
    code = "class A {}\nclass B extends A {}\nclass C extends B {}\n"
    code += "class D extends C {}\nclass E extends D {}\n"
    f.write_text(code)
    result = run(f, "typescript")
    assert result["success"] is True
    assert result["files_analyzed"] == 1


@pytest.mark.unit
def test_inheritance_run_with_files_list_mixed(tmp_path):
    """run() with explicit files list containing .py and .ts (lines 153-157)."""
    py_file = tmp_path / "mod.py"
    py_file.write_text("class X: pass\n")
    ts_file = tmp_path / "svc.ts"
    ts_file.write_text("class Y {}\n")
    result = run(tmp_path, "python", files=[py_file, ts_file])
    assert result["success"] is True
    assert result["files_analyzed"] == 2


@pytest.mark.unit
def test_inheritance_check_non_python_oserror_skips(tmp_path):
    """OSError reading file in _check_non_python (lines 112-113) → skipped."""
    ts_file = tmp_path / "svc.ts"
    ts_file.write_text("class A {}\nclass B extends A {}\n")
    with patch("pathlib.Path.read_text", side_effect=OSError("no access")):
        result = run(tmp_path, "typescript")
    assert result["success"] is True
    assert result["violations"] == []
