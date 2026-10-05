"""SQL rules of the five SSA checkers that analyze .sql files (#42).

Every rule has a positive case and a safe form of the same statement that must
not match — parameterized dynamic SQL is the norm, not the exception.
"""

from pathlib import Path

import pytest
from ssa.checkers import (
    check_concurrency,
    check_error_handling,
    check_misconfiguration,
    check_security,
    check_sensitive_data,
)
from ssa.hybrid import scan_patterns


def _sql(tmp_path: Path, text: str) -> Path:
    f = tmp_path / "proc.sql"
    f.write_text(text, encoding="utf-8")
    return f


def _security(tmp_path, text):
    return [v["message"] for v in check_security._mechanical_check(_sql(tmp_path, text), tmp_path, "sql")]


def _table(tmp_path, text, module):
    found = scan_patterns(_sql(tmp_path, text), tmp_path, "sql", "P", module._RULES)
    return [v["message"] for v in found]


class TestSecurityInjection:
    @pytest.mark.parametrize(
        "text",
        [
            "EXEC('SELECT * FROM orders WHERE id = ' + @id)",
            "EXEC(@sql + @filter)",
            "SET @sql = 'SELECT * FROM orders WHERE name = ''' + @name + ''''",
            "EXEC sp_executesql N'SELECT * FROM orders WHERE id = ' + @id",
            "EXECUTE 'SELECT * FROM orders WHERE id = ' || p_id;",
            "EXECUTE format('SELECT * FROM %s', p_table);",
        ],
    )
    def test_dynamic_sql_concatenation_flagged(self, tmp_path, text):
        assert any("SQL" in m or "format()" in m for m in _security(tmp_path, text))

    @pytest.mark.parametrize(
        "text",
        [
            "EXEC sp_executesql @sql, N'@id INT', @id = @id",
            "EXECUTE format('SELECT * FROM %I WHERE id = %L', p_table, p_id);",
            "EXECUTE 'SELECT * FROM orders WHERE id = $1' USING p_id;",
            "SET @greeting = 'Hello ' + @name",
            "SELECT * FROM orders WHERE id = @id",
        ],
    )
    def test_parameterized_sql_not_flagged(self, tmp_path, text):
        assert _security(tmp_path, text) == []


class TestSensitiveData:
    def test_secret_printed(self, tmp_path):
        assert _table(tmp_path, "PRINT 'password is ' + @password", check_sensitive_data)

    def test_plain_print_not_flagged(self, tmp_path):
        assert _table(tmp_path, "PRINT 'order saved'", check_sensitive_data) == []

    def test_error_detail_returned(self, tmp_path):
        assert _table(tmp_path, "SELECT ERROR_MESSAGE() AS detail;", check_sensitive_data)

    def test_sqlerrm_raised_to_caller(self, tmp_path):
        assert _table(tmp_path, "RAISE EXCEPTION 'failed: %', SQLERRM;", check_sensitive_data)

    def test_generic_raise_not_flagged(self, tmp_path):
        assert _table(tmp_path, "RAISE EXCEPTION 'order not found';", check_sensitive_data) == []

    def test_password_in_dblink(self, tmp_path):
        assert _table(tmp_path, "SELECT dblink_connect('host=db user=app password=abc');", check_sensitive_data)

    def test_dblink_with_user_mapping_not_flagged(self, tmp_path):
        assert _table(tmp_path, "SELECT dblink_connect('reporting_server');", check_sensitive_data) == []


class TestMisconfiguration:
    @pytest.mark.parametrize(
        "text",
        [
            "GRANT ALL ON orders TO app_user;",
            "GRANT SELECT ON orders TO PUBLIC;",
            "EXEC sp_configure 'xp_cmdshell', 1;",
            "ALTER DATABASE Shop SET TRUSTWORTHY ON;",
        ],
    )
    def test_flagged(self, tmp_path, text):
        assert _table(tmp_path, text, check_misconfiguration)

    @pytest.mark.parametrize(
        "text",
        [
            "GRANT SELECT, INSERT ON orders TO app_role;",
            "EXEC sp_configure 'xp_cmdshell', 0;",
            "ALTER DATABASE Shop SET TRUSTWORTHY OFF;",
            "REVOKE ALL ON orders FROM PUBLIC;",
        ],
    )
    def test_safe_forms_not_flagged(self, tmp_path, text):
        assert _table(tmp_path, text, check_misconfiguration) == []


class TestConcurrency:
    def _messages(self, tmp_path, text):
        return [v["message"] for v in check_concurrency._mechanical_check(_sql(tmp_path, text), tmp_path, "sql")]

    def test_nolock(self, tmp_path):
        assert self._messages(tmp_path, "SELECT total FROM orders WITH (NOLOCK)")

    def test_read_uncommitted(self, tmp_path):
        assert self._messages(tmp_path, "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")

    def test_read_committed_not_flagged(self, tmp_path):
        assert self._messages(tmp_path, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED;") == []


class TestErrorHandling:
    def _found(self, text):
        return check_error_handling._detect_non_python_violations(text, "proc.sql", "sql")

    def test_empty_catch_across_lines_reports_the_opening_line(self):
        text = "BEGIN TRY\n  DELETE FROM orders;\nEND TRY\nBEGIN CATCH\nEND CATCH\n"
        found = self._found(text)
        assert [(v["line"], v["message"]) for v in found] == [(4, "Empty CATCH block")]

    def test_handled_catch_not_flagged(self):
        assert self._found("BEGIN CATCH\n  THROW;\nEND CATCH\n") == []

    def test_when_others_then_null(self):
        text = "BEGIN\n  DELETE FROM orders;\nEXCEPTION\n  WHEN OTHERS THEN\n    NULL;\nEND;\n"
        assert [v["line"] for v in self._found(text)] == [4]

    def test_when_others_reraise_not_flagged(self):
        assert self._found("EXCEPTION\n  WHEN OTHERS THEN\n    RAISE;\n") == []


@pytest.mark.parametrize(
    "module", [check_security, check_sensitive_data, check_misconfiguration, check_concurrency, check_error_handling]
)
def test_checker_accepts_sql_files(module):
    assert "query" in module.FILE_KINDS
