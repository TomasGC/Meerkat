"""Unit tests for check_security — mechanical path only (no I/O, AI mocked out)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers.check_security import run, _SECRET_PATTERNS, _INJECTION_PATTERNS, _mechanical_check, _PRINCIPLE


# --- helpers -----------------------------------------------------------------

def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


# --- _SECRET_PATTERNS --------------------------------------------------------

class TestSecretPatterns:
    def test_detects_hardcoded_password(self, tmp_path):
        f = _make_file(tmp_path, "config.py", 'password = "hunter2"\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("HARDCODED_SECRET" in v["message"] or "secret" in v["message"].lower() for v in violations)

    def test_detects_api_key(self, tmp_path):
        f = _make_file(tmp_path, "client.py", 'api_key = "sk-abcdef1234567890"\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("secret" in v["message"].lower() or "api_key" in v["message"].lower() for v in violations)

    def test_clean_file_no_violations(self, tmp_path):
        f = _make_file(tmp_path, "clean.py", 'password = os.environ["PASSWORD"]\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert violations == []


# --- _INJECTION_PATTERNS -----------------------------------------------------

class TestInjectionPatterns:
    def test_detects_python_sql_percent_format(self, tmp_path):
        f = _make_file(tmp_path, "dao.py",
                       'cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("sql" in v["message"].lower() or "injection" in v["message"].lower() for v in violations)

    def test_detects_python_sql_fstring(self, tmp_path):
        f = _make_file(tmp_path, "dao.py",
                       'db.execute(f"SELECT * FROM orders WHERE id = {order_id}")\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("sql" in v["message"].lower() or "injection" in v["message"].lower() for v in violations)

    def test_no_sql_violation_for_unrelated_code(self, tmp_path):
        f = _make_file(tmp_path, "utils.py",
                       'result = compute(x, y)\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert all("sql" not in v["message"].lower() for v in violations)


class TestSsrfAndOpenRedirect:
    def test_detects_python_ssrf(self, tmp_path):
        f = _make_file(tmp_path, "proxy.py", 'requests.get(f"https://{host}/data")\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("SSRF" in v["message"] for v in violations)

    def test_python_constant_url_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "proxy.py", 'requests.get("https://api.internal/data")\n')
        assert _mechanical_check(f, tmp_path, "python") == []

    def test_detects_python_open_redirect(self, tmp_path):
        f = _make_file(tmp_path, "views.py", 'return redirect(request.args["next"])\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("open redirect" in v["message"] for v in violations)

    def test_detects_node_ssrf(self, tmp_path):
        f = _make_file(tmp_path, "proxy.js", 'await fetch(req.query.url);\n')
        violations = _mechanical_check(f, tmp_path, "javascript")
        assert any("SSRF" in v["message"] for v in violations)

    def test_detects_express_open_redirect(self, tmp_path):
        f = _make_file(tmp_path, "routes.js", 'res.redirect(req.query.next);\n')
        violations = _mechanical_check(f, tmp_path, "javascript")
        assert any("open redirect" in v["message"] for v in violations)

    def test_detects_go_ssrf(self, tmp_path):
        f = _make_file(tmp_path, "proxy.go", '\tresp, err := http.Get(r.FormValue("url"))\n')
        violations = _mechanical_check(f, tmp_path, "go")
        assert any("SSRF" in v["message"] for v in violations)

    def test_detects_csharp_ssrf(self, tmp_path):
        f = _make_file(tmp_path, "Proxy.cs", '        var res = await _client.GetAsync(Request.Query["url"]);\n')
        violations = _mechanical_check(f, tmp_path, "csharp")
        assert any("SSRF" in v["message"] for v in violations)


class TestMassAssignment:
    def test_detects_python_splat(self, tmp_path):
        f = _make_file(tmp_path, "views.py", "user = User(**request.json)\n")
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("mass assignment" in v["message"] for v in violations)

    def test_detects_node_spread(self, tmp_path):
        f = _make_file(tmp_path, "routes.ts", "await User.create({ ...req.body });\n")
        violations = _mechanical_check(f, tmp_path, "typescript")
        assert any("mass assignment" in v["message"] for v in violations)

    def test_detects_csharp_try_update_model(self, tmp_path):
        f = _make_file(tmp_path, "Controller.cs", "        await TryUpdateModelAsync(user);\n")
        violations = _mechanical_check(f, tmp_path, "csharp")
        assert any("mass assignment" in v["message"] for v in violations)

    def test_explicit_field_binding_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "views.py", 'user = User(email=request.json["email"])\n')
        assert _mechanical_check(f, tmp_path, "python") == []


class TestJwtWeaknesses:
    def test_detects_verify_false(self, tmp_path):
        f = _make_file(tmp_path, "auth.py", "claims = jwt.decode(token, verify=False)\n")
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("verify=False" in v["message"] for v in violations)

    def test_detects_none_algorithm(self, tmp_path):
        f = _make_file(tmp_path, "auth.py", 'claims = jwt.decode(token, key, algorithms=["none"])\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("none algorithm" in v["message"] for v in violations)

    def test_detects_alg_none_header(self, tmp_path):
        f = _make_file(tmp_path, "auth.js", 'const header = { "alg": "none" };\n')
        violations = _mechanical_check(f, tmp_path, "javascript")
        assert any("alg=none" in v["message"] for v in violations)

    def test_detects_csharp_disabled_validation(self, tmp_path):
        f = _make_file(tmp_path, "Startup.cs", "            ValidateIssuer = false,\n")
        violations = _mechanical_check(f, tmp_path, "csharp")
        assert any("validation disabled" in v["message"] for v in violations)

    def test_signed_validation_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "Startup.cs", "            ValidateIssuer = true,\n")
        assert _mechanical_check(f, tmp_path, "csharp") == []


class TestRedos:
    def test_detects_nested_quantifier_in_regex(self, tmp_path):
        f = _make_file(tmp_path, "validate.py", 're.compile(r"^(a+)+$")\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("ReDoS" in v["message"] for v in violations)

    def test_arithmetic_is_not_flagged(self, tmp_path):
        f = _make_file(tmp_path, "calc.py", "total = (a + b) * c\n")
        assert _mechanical_check(f, tmp_path, "python") == []

    def test_simple_regex_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "validate.py", 're.compile(r"^[a-z]+$")\n')
        assert _mechanical_check(f, tmp_path, "python") == []


class TestCredentialInUrl:
    def test_detects_token_in_query_string(self, tmp_path):
        f = _make_file(tmp_path, "client.py", 'url = base + "/data?token=" + tok\n')
        violations = _mechanical_check(f, tmp_path, "python")
        assert any("URL query string" in v["message"] for v in violations)


class TestShellAndRazorPatterns:
    def test_detects_invoke_expression(self, tmp_path):
        f = _make_file(tmp_path, "run.ps1", "Invoke-Expression $userInput\n")
        violations = _mechanical_check(f, tmp_path, "powershell")
        assert any("Invoke-Expression" in v["message"] for v in violations)

    def test_detects_plaintext_secure_string(self, tmp_path):
        f = _make_file(tmp_path, "run.ps1", "ConvertTo-SecureString $p -AsPlainText -Force\n")
        violations = _mechanical_check(f, tmp_path, "powershell")
        assert any("Plaintext secret" in v["message"] for v in violations)

    def test_detects_bash_eval(self, tmp_path):
        f = _make_file(tmp_path, "run.sh", 'eval "$USER_CMD"\n')
        violations = _mechanical_check(f, tmp_path, "bash")
        assert any("command injection" in v["message"] for v in violations)

    def test_detects_curl_pipe_shell(self, tmp_path):
        f = _make_file(tmp_path, "install.sh", "curl -sSL https://example.com/i.sh | sh\n")
        violations = _mechanical_check(f, tmp_path, "bash")
        assert any("remote code execution" in v["message"] for v in violations)

    def test_detects_razor_html_raw(self, tmp_path):
        f = _make_file(tmp_path, "Index.cshtml", "@Html.Raw(Model.Bio)\n")
        violations = _mechanical_check(f, tmp_path, "razor")
        assert any("Html.Raw" in v["message"] for v in violations)

    def test_encoded_razor_output_is_clean(self, tmp_path):
        f = _make_file(tmp_path, "Index.cshtml", "@Model.Bio\n")
        assert _mechanical_check(f, tmp_path, "razor") == []


# --- run() -------------------------------------------------------------------

class TestRunFunction:
    def test_returns_correct_schema(self, tmp_path):
        with patch("checkers.check_security.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["principle"] == _PRINCIPLE
        assert result["success"] is True
        assert "violations" in result
        assert "files_analyzed" in result
        assert "duration_ms" in result

    def test_empty_dir_no_violations(self, tmp_path):
        with patch("checkers.check_security.check_server_available", return_value=False):
            result = run(tmp_path, "python")
        assert result["violations"] == []

    def test_files_kwarg_scopes_analysis(self, tmp_path):
        clean = _make_file(tmp_path, "clean.py", 'x = 1\n')
        dirty = _make_file(tmp_path, "dirty.py", 'password = "secret123"\n')
        with patch("checkers.check_security.check_server_available", return_value=False):
            result = run(tmp_path, "python", files=[clean])
        assert all(v["file"] != "dirty.py" for v in result["violations"])
