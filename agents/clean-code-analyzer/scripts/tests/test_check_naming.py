"""Tests for check_naming — magic numbers, magic strings, single-letter vars."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from checkers.check_naming import _check_file


class TestMagicNumbers:
    def test_detects_magic_number(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("timeout = 3600\n")
        violations = _check_file(f, tmp_path)
        assert any("3600" in v["message"] for v in violations)

    def test_allows_ok_numbers(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("x = 0\ny = 1\nz = 200\n")
        violations = _check_file(f, tmp_path)
        magic = [v for v in violations if "magic_number" in v["message"].lower() or "Magic number" in v["message"]]
        assert len(magic) == 0

    def test_no_magic_numbers_in_test_files(self, tmp_path):
        f = tmp_path / "test_thing.py"
        f.write_text("assert result == 9999\n")
        violations = _check_file(f, tmp_path)
        magic = [v for v in violations if "magic" in v["message"].lower()]
        assert len(magic) == 0


class TestSingleLetterVars:
    def test_detects_single_letter_outside_loop(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("a = some_value()\n")
        violations = _check_file(f, tmp_path)
        single = [v for v in violations if "Single-letter" in v["message"] and "`a`" in v["message"]]
        assert len(single) >= 1

    def test_allows_loop_variable(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("for i in range(10):\n    print(i)\n")
        violations = _check_file(f, tmp_path)
        loop_violations = [v for v in violations if "`i`" in v.get("message", "")]
        assert len(loop_violations) == 0

    def test_allows_allowed_abbreviations(self, tmp_path):
        f = tmp_path / "ok.py"
        f.write_text("id = get_id()\ndb = get_db()\n")
        violations = _check_file(f, tmp_path)
        abbr_violations = [v for v in violations if "`id`" in v.get("message", "") or "`db`" in v.get("message", "")]
        assert len(abbr_violations) == 0


class TestRunSignature:
    def test_accepts_files_param(self, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1\n")
        from checkers.check_naming import run
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
        assert result["files_analyzed"] == 1


@pytest.mark.parametrize("code,should_flag", [
    # Single-letter in for loop — should NOT flag
    ("for i in range(10):\n    print(i)\n", False),
    ("for j, item in enumerate(items):\n    pass\n", False),
    # Single-letter outside loop (not x/y/z which are math-exempt) — SHOULD flag
    ("a = compute_total()\n", True),
    # Named constant definition — should NOT flag magic number
    ("MAX_RETRIES = 3600\n", False),
    # Magic number in condition — SHOULD flag
    ("if retries > 3600:\n    timeout()\n", True),
    # Named constant used in condition — should NOT flag
    ("MAX_RETRIES = 3600\nif retries > MAX_RETRIES:\n    pass\n", False),
    # Allowed abbreviations — should NOT flag (these are > 1 char, won't match single-letter regex)
    ("def get_user(id):\n    pass\n", False),
    ("err = validate()\n", False),
])
def test_naming_parametrized(tmp_path, code, should_flag):
    f = tmp_path / "module.py"
    f.write_text(code)
    from checkers.check_naming import _check_file
    violations = _check_file(f, tmp_path)
    has_violations = len(violations) > 0
    assert has_violations == should_flag, (
        f"Code:\n{code!r}\nExpected violations={should_flag}, got {violations}"
    )
