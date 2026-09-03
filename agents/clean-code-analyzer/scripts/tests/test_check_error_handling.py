"""Tests for check_error_handling — Python AST-based detection."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from checkers.check_error_handling import _check_python_file


class TestEmptyExcept:
    def test_detects_bare_except_pass(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("try:\n    x()\nexcept:\n    pass\n")
        violations = _check_python_file(f, tmp_path)
        assert any("pass" in v["message"] or "bare" in v["message"].lower() for v in violations)
        assert all(v["severity"] == "high" for v in violations)

    def test_detects_except_exception_no_log(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("try:\n    x()\nexcept Exception:\n    y = 1\n")
        violations = _check_python_file(f, tmp_path)
        assert len(violations) >= 1

    def test_no_violation_when_logged(self, tmp_path):
        f = tmp_path / "good.py"
        f.write_text(
            "import logging\nlogger = logging.getLogger(__name__)\n"
            "try:\n    x()\nexcept Exception as e:\n    logger.error(e)\n"
        )
        violations = _check_python_file(f, tmp_path)
        assert len(violations) == 0

    def test_no_violation_when_reraised(self, tmp_path):
        f = tmp_path / "good.py"
        f.write_text("try:\n    x()\nexcept Exception:\n    raise\n")
        violations = _check_python_file(f, tmp_path)
        assert len(violations) == 0

    def test_syntax_error_returns_empty(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def (:\n    pass")
        violations = _check_python_file(f, tmp_path)
        assert violations == []


class TestRunSignature:
    def test_accepts_files_param(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        from checkers.check_error_handling import run
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
        assert result["files_analyzed"] == 1


@pytest.mark.parametrize("code,should_flag", [
    # Empty bare except — SHOULD flag
    ("try:\n    risky()\nexcept:\n    pass\n", True),
    # except Exception with only pass — SHOULD flag
    ("try:\n    risky()\nexcept Exception:\n    pass\n", True),
    # Caught and logged — should NOT flag
    (
        "import logging\nlogger = logging.getLogger(__name__)\n"
        "try:\n    risky()\nexcept Exception as e:\n    logger.error(e)\n",
        False,
    ),
    # Caught and re-raised — should NOT flag
    ("try:\n    risky()\nexcept Exception:\n    raise\n", False),
    # Wrapped re-raise — should NOT flag
    (
        "try:\n    risky()\nexcept ValueError as e:\n"
        "    raise RuntimeError('wrapped') from e\n",
        False,
    ),
    # Clean code — should NOT flag
    ("def compute(x):\n    return x * 2\n", False),
])
def test_error_handling_parametrized(tmp_path, code, should_flag):
    f = tmp_path / "module.py"
    f.write_text(code)
    from checkers.check_error_handling import _check_python_file
    violations = _check_python_file(f, tmp_path)
    has_violations = len(violations) > 0
    assert has_violations == should_flag, (
        f"Code:\n{code!r}\nExpected violations={should_flag}, got {violations}"
    )
