"""The `{language}` slot names a file's dialect (#42): T-SQL / PostgreSQL / SQL, never "mixed".

call_model_async is replaced; it records every prompt. No server needed.
"""

from pathlib import Path
from unittest.mock import patch

import lib.ai.model_utils as mu
import pytest

_TSQL = "CREATE PROCEDURE dbo.GetOrder @id INT AS\nBEGIN TRY\n  SELECT * FROM [dbo].orders WHERE id = @id\nEND TRY\n"
_PGSQL = (
    "CREATE FUNCTION get_order(p_id int) RETURNS SETOF orders AS $$\n  SELECT * FROM orders;\n$$ LANGUAGE plpgsql;\n"
)


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "p.prompt").write_text("LANG={language}\n{source}", encoding="utf-8")
    return d


def _run(tmp_path, prompts_dir, files: dict[str, str], language: str, extra_slots=None) -> dict[str, str]:
    paths = []
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
        paths.append(tmp_path / name)
    seen: dict[str, str] = {}

    async def fake(prompt, role="analyzer", timeout=None):
        name = next(n for n, text in files.items() if text in prompt)
        seen[name] = prompt.splitlines()[0]
        return "[]"

    with patch.object(mu, "call_model_async", fake):
        mu.analyze_files_parallel(
            paths,
            language,
            "analyzer",
            "p",
            prompts_dir=prompts_dir,
            extra_slots={tmp_path / k: v for k, v in (extra_slots or {}).items()},
        )
    return seen


def test_each_sql_file_gets_its_own_dialect(tmp_path, prompts_dir):
    seen = _run(tmp_path, prompts_dir, {"a.sql": _TSQL, "b.sql": _PGSQL}, "sql")
    assert seen == {"a.sql": "LANG=T-SQL", "b.sql": "LANG=PostgreSQL"}


def test_unrecognized_sql_is_plain_sql(tmp_path, prompts_dir):
    assert _run(tmp_path, prompts_dir, {"a.sql": "SELECT 1;\n"}, "sql") == {"a.sql": "LANG=SQL"}


def test_languages_without_dialects_are_unchanged(tmp_path, prompts_dir):
    assert _run(tmp_path, prompts_dir, {"a.py": "x = 1\n"}, "python") == {"a.py": "LANG=python"}


def test_caller_language_slot_wins(tmp_path, prompts_dir):
    seen = _run(tmp_path, prompts_dir, {"a.sql": _TSQL}, "sql", extra_slots={"a.sql": {"language": "Custom"}})
    assert seen == {"a.sql": "LANG=Custom"}
