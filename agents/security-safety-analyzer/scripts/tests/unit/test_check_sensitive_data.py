"""Unit tests for checkers/check_sensitive_data.py — mechanical layer only (server patched off)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers import check_sensitive_data


def _run(tmp_path: Path, name: str, content: str, language: str) -> list[dict]:
    f = tmp_path / name
    f.write_text(content)
    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = check_sensitive_data.run(tmp_path, language, files=[f])
    assert result["success"] is True
    assert result["principle"] == "SensitiveData"
    return result["violations"]


class TestPythonChecks:
    def test_detects_secret_in_logger(self, tmp_path):
        v = _run(tmp_path, "auth.py", 'logger.info("password=%s", password)\n', "python")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_secret_in_print(self, tmp_path):
        v = _run(tmp_path, "auth.py", "print(api_key)\n", "python")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_traceback_returned_to_caller(self, tmp_path):
        v = _run(tmp_path, "api.py", "return jsonify(error=traceback.format_exc())\n", "python")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_detects_traceback_printed(self, tmp_path):
        v = _run(tmp_path, "api.py", "print(traceback.format_exc())\n", "python")
        assert v and v[0]["severity"] == "medium"

    def test_detects_exception_string_returned(self, tmp_path):
        v = _run(tmp_path, "api.py", "return jsonify(error=str(e))\n", "python")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_masked_logging_is_clean(self, tmp_path):
        code = 'logger.info("user %s authenticated", user_id)\n'
        assert _run(tmp_path, "auth.py", code, "python") == []


class TestCSharpChecks:
    def test_detects_secret_in_logger(self, tmp_path):
        code = '_logger.LogInformation("token {Token}", token);\n'
        v = _run(tmp_path, "Auth.cs", code, "csharp")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_secret_in_console(self, tmp_path):
        v = _run(tmp_path, "Auth.cs", 'Console.WriteLine("cvv: " + cvv);\n', "csharp")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_exception_written_to_console(self, tmp_path):
        v = _run(tmp_path, "Api.cs", "Console.WriteLine(ex);\n", "csharp")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_detects_stack_trace_in_response(self, tmp_path):
        v = _run(tmp_path, "Api.cs", "return BadRequest(ex.StackTrace);\n", "csharp")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_generic_error_response_is_clean(self, tmp_path):
        code = '_logger.LogError(ex, "request failed");\nreturn BadRequest("Invalid request");\n'
        assert _run(tmp_path, "Api.cs", code, "csharp") == []


class TestJavaScriptChecks:
    def test_detects_secret_in_console(self, tmp_path):
        v = _run(tmp_path, "auth.js", "console.log(apiKey);\n", "javascript")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_secret_in_logger(self, tmp_path):
        v = _run(tmp_path, "auth.js", "logger.debug({ password });\n", "javascript")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_stack_in_response(self, tmp_path):
        v = _run(tmp_path, "api.js", "res.json({ error: err.stack });\n", "javascript")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_typescript_shares_javascript_rules(self, tmp_path):
        v = _run(tmp_path, "auth.ts", "console.log(privateKey);\n", "typescript")
        assert any("written to a log" in x["message"] for x in v)

    def test_identifier_logging_is_clean(self, tmp_path):
        assert _run(tmp_path, "auth.js", "console.log(userId);\n", "javascript") == []


class TestOtherLanguages:
    def test_detects_secret_in_go_log(self, tmp_path):
        v = _run(tmp_path, "auth.go", 'log.Printf("token %s", token)\n', "go")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_error_returned_by_http_error(self, tmp_path):
        v = _run(tmp_path, "api.go", "http.Error(w, err.Error(), 500)\n", "go")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_detects_secret_in_write_host(self, tmp_path):
        v = _run(tmp_path, "deploy.ps1", 'Write-Host "secret: $secret"\n', "powershell")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_exception_in_write_host(self, tmp_path):
        v = _run(tmp_path, "deploy.ps1", "Write-Host $_.Exception\n", "powershell")
        assert any("Internal error detail" in x["message"] for x in v)

    def test_detects_secret_echoed_in_bash(self, tmp_path):
        v = _run(tmp_path, "deploy.sh", 'echo "$API_KEY"\n', "bash")
        assert any("written to a log" in x["message"] for x in v)

    def test_detects_shell_tracing(self, tmp_path):
        v = _run(tmp_path, "deploy.sh", "set -x\n", "bash")
        assert any("Shell tracing" in x["message"] for x in v)

    def test_detects_stack_trace_in_razor_view(self, tmp_path):
        v = _run(tmp_path, "Error.cshtml", "<pre>@Model.Exception.StackTrace</pre>\n", "razor")
        assert any("Internal error detail" in x["message"] for x in v)


class TestUniversalRules:
    def test_detects_credential_in_url_for_any_language(self, tmp_path):
        v = _run(tmp_path, "client.go", 'url := "https://api/x?api_key=" + key\n', "go")
        assert any("URL query string" in x["message"] for x in v)

    def test_universal_rule_also_applies_to_python(self, tmp_path):
        v = _run(tmp_path, "client.py", 'url = f"https://api/x?token={t}"\n', "python")
        assert any("URL query string" in x["message"] for x in v)

    def test_url_without_credentials_is_clean(self, tmp_path):
        assert _run(tmp_path, "client.py", 'url = "https://api/x?page=2"\n', "python") == []
