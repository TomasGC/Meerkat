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
