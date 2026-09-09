"""Unit tests for checkers/check_misconfiguration.py — mechanical layer only (server patched off)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers import check_misconfiguration


def _run(tmp_path: Path, name: str, content: str, language: str) -> list[dict]:
    f = tmp_path / name
    f.write_text(content)
    with patch("common.hybrid.check_server_available", return_value=False):
        result = check_misconfiguration.run(tmp_path, language, files=[f])
    assert result["success"] is True
    assert result["principle"] == "Misconfiguration"
    return result["violations"]


def _run_discovered(tmp_path: Path, name: str, content: str) -> list[dict]:
    """Dockerfiles have no extension, so they are only reachable through discovery."""
    (tmp_path / name).write_text(content)
    with patch("common.hybrid.check_server_available", return_value=False):
        return check_misconfiguration.run(tmp_path, "mixed")["violations"]


class TestCSharpChecks:
    def test_detects_allow_any_origin(self, tmp_path):
        v = _run(tmp_path, "Startup.cs", "builder.AllowAnyOrigin();\n", "csharp")
        assert any("any origin" in x["message"] for x in v)

    def test_detects_always_true_origin_predicate(self, tmp_path):
        v = _run(tmp_path, "Startup.cs", "builder.SetIsOriginAllowed(_ => true);\n", "csharp")
        assert any("always returns true" in x["message"] for x in v)

    def test_detects_https_metadata_disabled(self, tmp_path):
        v = _run(tmp_path, "Auth.cs", "options.RequireHttpsMetadata = false;\n", "csharp")
        assert v and v[0]["severity"] == "high"

    def test_detects_developer_exception_page(self, tmp_path):
        v = _run(tmp_path, "Startup.cs", "app.UseDeveloperExceptionPage();\n", "csharp")
        assert any("Debug output enabled" in x["message"] for x in v)

    def test_detects_insecure_cookie(self, tmp_path):
        code = "var opts = new CookieOptions { Secure = false, SameSite = SameSiteMode.Lax };\n"
        v = _run(tmp_path, "Cookies.cs", code, "csharp")
        assert any("Secure or HttpOnly" in x["message"] for x in v)

    def test_detects_allow_anonymous(self, tmp_path):
        v = _run(tmp_path, "Api.cs", "[AllowAnonymous]\n", "csharp")
        assert v and v[0]["severity"] == "medium"

    def test_restricted_cors_is_clean(self, tmp_path):
        code = 'builder.WithOrigins("https://app.example.com").AllowCredentials();\n'
        assert _run(tmp_path, "Startup.cs", code, "csharp") == []


class TestPythonChecks:
    def test_detects_debug_true_setting(self, tmp_path):
        v = _run(tmp_path, "settings.py", "DEBUG = True\n", "python")
        assert any("Debug output enabled" in x["message"] for x in v)

    def test_detects_wildcard_allowed_hosts(self, tmp_path):
        v = _run(tmp_path, "settings.py", "ALLOWED_HOSTS = ['*']\n", "python")
        assert any("host header attacks" in x["message"] for x in v)

    def test_detects_flask_debug_run(self, tmp_path):
        v = _run(tmp_path, "app.py", "app.run(debug=True)\n", "python")
        assert any("Debug output enabled" in x["message"] for x in v)

    def test_detects_bind_all_interfaces(self, tmp_path):
        v = _run(tmp_path, "app.py", 'serve(host="0.0.0.0", port=8080)\n', "python")
        assert any("every interface" in x["message"] for x in v)

    def test_detects_cors_allow_all(self, tmp_path):
        v = _run(tmp_path, "settings.py", "CORS_ORIGIN_ALLOW_ALL = True\n", "python")
        assert any("any origin" in x["message"] for x in v)

    def test_production_settings_are_clean(self, tmp_path):
        code = "DEBUG = False\nALLOWED_HOSTS = ['app.example.com']\n"
        assert _run(tmp_path, "settings.py", code, "python") == []


class TestJavaScriptChecks:
    def test_detects_bare_cors_middleware(self, tmp_path):
        v = _run(tmp_path, "server.js", "app.use(cors());\n", "javascript")
        assert any("any origin" in x["message"] for x in v)

    def test_detects_wildcard_cors_origin(self, tmp_path):
        v = _run(tmp_path, "server.js", "app.use(cors({ origin: '*' }));\n", "javascript")
        assert any("any origin" in x["message"] for x in v)

    def test_detects_insecure_cookie(self, tmp_path):
        v = _run(tmp_path, "server.js", "res.cookie('sid', id, { httpOnly: false });\n", "javascript")
        assert any("Secure or HttpOnly" in x["message"] for x in v)

    def test_typescript_shares_javascript_rules(self, tmp_path):
        v = _run(tmp_path, "server.ts", "app.use(cors());\n", "typescript")
        assert any("any origin" in x["message"] for x in v)

    def test_restricted_cors_is_clean(self, tmp_path):
        code = "app.use(cors({ origin: ['https://app.example.com'] }));\n"
        assert _run(tmp_path, "server.js", code, "javascript") == []


class TestYamlChecks:
    def test_detects_privileged_container(self, tmp_path):
        v = _run(tmp_path, "deploy.yaml", "        privileged: true\n", "yaml")
        assert any("privileged" in x["message"] for x in v)

    def test_detects_writable_root_filesystem(self, tmp_path):
        v = _run(tmp_path, "deploy.yaml", "        readOnlyRootFilesystem: false\n", "yaml")
        assert v and v[0]["severity"] == "medium"

    def test_detects_host_namespace_sharing(self, tmp_path):
        v = _run(tmp_path, "deploy.yml", "  hostNetwork: true\n", "yaml")
        assert any("host namespace" in x["message"] for x in v)

    def test_detects_root_user(self, tmp_path):
        v = _run(tmp_path, "deploy.yaml", "        runAsUser: 0\n", "yaml")
        assert any("runs as root" in x["message"] for x in v)

    def test_detects_privilege_escalation(self, tmp_path):
        v = _run(tmp_path, "deploy.yaml", "        allowPrivilegeEscalation: true\n", "yaml")
        assert any("Privilege escalation" in x["message"] for x in v)

    def test_hardened_pod_spec_is_clean(self, tmp_path):
        code = (
            "      securityContext:\n"
            "        runAsNonRoot: true\n"
            "        runAsUser: 1000\n"
            "        allowPrivilegeEscalation: false\n"
            "        readOnlyRootFilesystem: true\n"
        )
        assert _run(tmp_path, "deploy.yaml", code, "yaml") == []


class TestDockerfileChecks:
    def test_detects_latest_tag(self, tmp_path):
        v = _run_discovered(tmp_path, "Dockerfile", "FROM node:latest\n")
        assert any("latest" in x["message"] for x in v)

    def test_detects_insecure_fetch(self, tmp_path):
        v = _run_discovered(tmp_path, "Dockerfile", "RUN wget --no-check-certificate https://x/a\n")
        assert any("Certificate validation skipped" in x["message"] for x in v)

    def test_detects_curl_pipe_shell(self, tmp_path):
        v = _run_discovered(tmp_path, "Dockerfile", "RUN curl -sSL https://x/i.sh | sh\n")
        assert any("pipes a downloaded script" in x["message"] for x in v)

    def test_pinned_base_image_is_clean(self, tmp_path):
        assert _run_discovered(tmp_path, "Dockerfile", "FROM node:20.11-alpine\n") == []


class TestShellChecks:
    def test_detects_chmod_777(self, tmp_path):
        v = _run(tmp_path, "setup.sh", "chmod -R 777 /var/data\n", "bash")
        assert any("World-writable" in x["message"] for x in v)

    def test_detects_permissive_umask(self, tmp_path):
        v = _run(tmp_path, "setup.sh", "umask 000\n", "bash")
        assert v and v[0]["severity"] == "high"

    def test_detects_relaxed_execution_policy(self, tmp_path):
        v = _run(tmp_path, "setup.ps1", "Set-ExecutionPolicy Bypass -Scope Process\n", "powershell")
        assert any("Execution policy relaxed" in x["message"] for x in v)

    def test_detects_everyone_grant(self, tmp_path):
        v = _run(tmp_path, "acl.ps1", "icacls C:\\data /grant Everyone:F\n", "powershell")
        assert any("Everyone granted access" in x["message"] for x in v)

    def test_restrictive_permissions_are_clean(self, tmp_path):
        assert _run(tmp_path, "setup.sh", "chmod 640 /var/data/config\numask 027\n", "bash") == []
