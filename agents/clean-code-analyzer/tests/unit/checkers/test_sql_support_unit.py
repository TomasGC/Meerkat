"""Unit tests for CCA on SQL files (#42) — comments and naming accept the `query` kind."""

from pathlib import Path

import pytest

import cca.orchestrate
from cca.checkers import check_comments, check_naming


def _messages(module, tmp_path: Path, text: str) -> list[str]:
    f = tmp_path / "proc.sql"
    f.write_text(text, encoding="utf-8")
    return [v["message"] for v in module.run(tmp_path, "sql", files=[f])["violations"]]


class TestCommentsOnSql:
    def test_todo_in_dash_comment(self, tmp_path):
        assert _messages(check_comments, tmp_path, "-- TODO: handle refunds\nSELECT 1;\n") == [
            "TODO comment — should be a tracked issue"
        ]

    def test_commented_out_query_block(self, tmp_path):
        text = "-- SELECT * FROM orders\n-- WHERE status = 3\nSELECT 1;\n"
        assert "Commented-out code block detected" in _messages(check_comments, tmp_path, text)

    def test_what_comment(self, tmp_path):
        assert "Comment explains WHAT the code does (obvious from code)" in _messages(
            check_comments, tmp_path, "-- update the stock\nUPDATE stock SET qty = qty - 1;\n"
        )

    def test_why_comment_is_clean(self, tmp_path):
        text = "-- Refunds settle overnight, so today's totals exclude them\nSELECT SUM(total) FROM orders;\n"
        assert _messages(check_comments, tmp_path, text) == []

    def test_hash_and_slash_files_keep_their_own_rules(self, tmp_path):
        """A `--` in Python is an operator, not a comment."""
        (tmp_path / "a.py").write_text("x = y -- 1  # fine\n", encoding="utf-8")
        assert check_comments.run(tmp_path, "python", files=[tmp_path / "a.py"])["violations"] == []


class TestNamingOnSql:
    def test_magic_number_in_query(self, tmp_path):
        assert "Magic number: 42" in _messages(check_naming, tmp_path, "SELECT * FROM orders WHERE status = 42;\n")

    def test_type_sizes_are_not_magic_numbers(self, tmp_path):
        text = "CREATE TABLE orders (name NVARCHAR(255), total DECIMAL(10, 2), code CHAR(12));\n"
        assert _messages(check_naming, tmp_path, text) == []

    def test_dash_comment_lines_are_skipped(self, tmp_path):
        assert _messages(check_naming, tmp_path, "-- status 42 means archived\nSELECT 1;\n") == []


@pytest.mark.parametrize("module", [check_comments, check_naming])
def test_accepts_sql(module):
    assert "query" in module.FILE_KINDS


@pytest.mark.parametrize("name", ["dry", "solid", "kiss", "yagni", "cqrs", "ddd", "lod", "slap", "inheritance"])
def test_other_checkers_stay_code_only(name):
    """Each exclusion is explained next to CHECKERS in orchestrate.py."""
    import importlib

    module = importlib.import_module(cca.orchestrate.CHECKERS[name])
    assert "query" not in getattr(module, "FILE_KINDS", ("code",))
