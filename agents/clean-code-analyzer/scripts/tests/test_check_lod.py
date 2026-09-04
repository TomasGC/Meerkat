"""Tests for check_lod — Law of Demeter violation detection."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from checkers.check_lod import _check_file


@pytest.mark.parametrize("code,should_flag", [
    # Deep method chain (3 calls) — SHOULD flag
    ("val = a.get_b().get_c().get_d()\n", True),
    # Property chain depth 4 — SHOULD flag
    ("result = obj.service.repository.find_by_id(42)\n", True),
    # Fluent query builder — should NOT flag (exempt: .filter()
    ("query = db.query(User).filter(User.active == True).order_by(User.name).all()\n", False),
    # Two-level property — should NOT flag
    ("name = user.profile.name\n", False),
    # One-level call — should NOT flag
    ("result = service.get_user(42)\n", False),
    # self.x.y — should NOT flag (self. exempt)
    ("value = self.config.timeout\n", False),
    # Chained assertions (exempt: .should.)
    ("x.should.equal(1).and_.be.ok\n", False),
])
def test_lod_parametrized(tmp_path, code, should_flag):
    f = tmp_path / "module.py"
    f.write_text(code)
    violations = _check_file(f, tmp_path)
    has_violations = len(violations) > 0
    assert has_violations == should_flag, (
        f"Code:\n{code!r}\nExpected violations={should_flag}, got {violations}"
    )


class TestRunSignature:
    def test_accepts_files_param(self, tmp_path):
        f = tmp_path / "src.py"
        f.write_text("x = 1\n")
        from checkers.check_lod import run
        result = run(tmp_path, "python", files=[f])
        assert result["success"] is True
        assert result["files_analyzed"] == 1

    def test_empty_file_no_violations(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        from checkers.check_lod import run
        result = run(tmp_path, "python", files=[f])
        assert result["violations"] == []
