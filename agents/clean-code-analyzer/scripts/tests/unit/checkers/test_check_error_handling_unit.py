"""Unit tests for checkers/check_error_handling.py — AST-based, no Ollama."""

from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from checkers.check_error_handling import run, _detect_non_python_violations, _check_python_file


def _wrap_try(handler_code: str) -> str:
    """Wrap handler code in a valid try/except block."""
    return handler_code


@pytest.mark.unit
@pytest.mark.parametrize("code,should_flag", [
    # Bare except with pass → flag (swallowed)
    ("try:\n    risky()\nexcept:\n    pass\n", True),
    # Generic Exception with pass → flag (swallowed)
    ("try:\n    risky()\nexcept Exception:\n    pass\n", True),
    # Exception with log + raise → no flag
    (
        "try:\n    risky()\nexcept Exception as e:\n    logger.error(e)\n    raise\n",
        False,
    ),
    # Specific exception with chained raise → no flag
    (
        "try:\n    risky()\nexcept ValueError as e:\n    raise RuntimeError('wrapped') from e\n",
        False,
    ),
    # Exception caught, only returns (no log, no raise) → flag
    (
        "try:\n    risky()\nexcept Exception as e:\n    return default\n",
        True,
    ),
])
def test_error_handling(tmp_path, code, should_flag):
    """Parametrized error handling detection check."""
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
def test_error_handling_return_schema(tmp_path):
    """Return dict has required keys."""
    (tmp_path / "mod.py").write_text("x = 1\n")
    result = run(tmp_path, "python")
    assert "principle" in result
    assert result["principle"] == "ErrorHandling"
    assert "success" in result
    assert "violations" in result
    assert "files_analyzed" in result
    assert "duration_ms" in result


# ── _detect_non_python_violations (pure function after refactoring B) ───────────

@pytest.mark.unit
def test_detect_non_python_violations_typescript_empty_catch():
    """Empty TypeScript catch block flagged as error handling violation."""
    content = "try {\n  risky();\n} catch (e) {}\n"
    result = _detect_non_python_violations(content, "app.ts", "typescript")
    assert len(result) >= 1
    assert result[0]["principle"] == "ErrorHandling"
    assert result[0]["severity"] == "high"


@pytest.mark.unit
def test_detect_non_python_violations_go_discarded_error():
    """Go explicit error discard with _ flagged."""
    content = "_ = service.DoSomething()\n"
    result = _detect_non_python_violations(content, "main.go", "go")
    assert len(result) >= 1
    assert result[0]["principle"] == "ErrorHandling"


@pytest.mark.unit
def test_detect_non_python_violations_unknown_language_returns_empty():
    """Language with no grep patterns → empty list (no crash)."""
    result = _detect_non_python_violations("some code", "mod.lua", "lua")
    assert result == []


@pytest.mark.unit
def test_detect_non_python_violations_powershell_silent_continue():
    """PowerShell -ErrorAction SilentlyContinue flagged."""
    content = "Remove-Item $path -ErrorAction SilentlyContinue\n"
    result = _detect_non_python_violations(content, "script.ps1", "powershell")
    assert len(result) >= 1
    assert result[0]["severity"] == "high"


# ── _check_python_file SyntaxError ──────────────────────────────────────────────

@pytest.mark.unit
def test_check_python_file_syntax_error_returns_empty(tmp_path):
    """File with SyntaxError → returns [], no exception raised."""
    f = tmp_path / "broken.py"
    f.write_text("def foo(\n  # unclosed parenthesis\n")
    result = _check_python_file(f, tmp_path)
    assert result == []


# ── bare except with non-empty body (no raise / no log) ─────────────────────────

@pytest.mark.unit
def test_error_handling_bare_except_with_assignment_flagged(tmp_path):
    """Bare `except:` with body that neither raises nor logs → flagged."""
    code = "try:\n    risky()\nexcept:\n    x = 1\n"
    (tmp_path / "mod.py").write_text(code)
    result = run(tmp_path, "python")
    assert result["success"] is True
    assert len(result["violations"]) >= 1


# ── _detect_non_python_violations: Go empty error check ─────────────────────────

@pytest.mark.unit
def test_detect_non_python_violations_go_empty_error_check():
    """Go `if err != nil {}` (empty block on one line) → ErrorHandling violation."""
    content = "if err != nil {}\n"
    result = _detect_non_python_violations(content, "main.go", "go")
    assert len(result) >= 1
    assert result[0]["principle"] == "ErrorHandling"


# ── run() with non-Python file ───────────────────────────────────────────────────

@pytest.mark.unit
def test_error_handling_run_with_single_go_file(tmp_path):
    """run() called with a single .go file path → success, files_analyzed=1."""
    f = tmp_path / "main.go"
    f.write_text("_ = service.DoSomething()\n")
    result = run(f, "go")
    assert result["success"] is True
    assert result["files_analyzed"] == 1


@pytest.mark.unit
def test_error_handling_run_with_typescript_directory(tmp_path):
    """run() on directory containing .ts file → dispatches _check_non_python, no crash."""
    (tmp_path / "app.ts").write_text("try { risky(); } catch (e) {}\n")
    result = run(tmp_path, "typescript")
    assert result["success"] is True
    assert isinstance(result["violations"], list)


@pytest.mark.unit
def test_error_handling_run_with_files_list(tmp_path):
    """run() with explicit files list (line 148 path) → only those files analyzed."""
    f = tmp_path / "mod.go"
    f.write_text("_ = svc.Get()\n")
    result = run(tmp_path, "go", files=[f])
    assert result["success"] is True
    assert result["files_analyzed"] == 1


@pytest.mark.unit
def test_error_handling_check_non_python_oserror_skips(tmp_path):
    """_check_non_python OSError path (lines 136-137) → returns []."""
    from unittest.mock import patch
    f = tmp_path / "app.ts"
    f.write_text("try {} catch(e) {}\n")
    with patch("pathlib.Path.read_text", side_effect=OSError("no access")):
        from checkers.check_error_handling import _check_non_python
        result = _check_non_python(f, tmp_path, "typescript")
    assert result == []
