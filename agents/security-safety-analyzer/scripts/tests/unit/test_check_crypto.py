"""Unit tests for checkers/check_crypto.py — mechanical layer only (server patched off)."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from checkers import check_crypto


def _run(tmp_path: Path, name: str, content: str, language: str) -> list[dict]:
    f = tmp_path / name
    f.write_text(content)
    with patch("lib.engine.hybrid.check_server_available", return_value=False):
        result = check_crypto.run(tmp_path, language, files=[f])
    assert result["success"] is True
    assert result["principle"] == "Crypto"
    return result["violations"]


class TestPythonChecks:
    def test_detects_md5(self, tmp_path):
        v = _run(tmp_path, "hash.py", "digest = hashlib.md5(data).hexdigest()\n", "python")
        assert any("Weak hash" in x["message"] for x in v)

    def test_detects_weak_random(self, tmp_path):
        v = _run(tmp_path, "tok.py", "token = random.randint(0, 999999)\n", "python")
        assert any("unguessable" in x["message"] for x in v)

    def test_detects_disabled_tls_verification(self, tmp_path):
        v = _run(tmp_path, "http.py", "requests.get(url, verify=False)\n", "python")
        assert any("certificate validation disabled" in x["message"] for x in v)

    def test_detects_unverified_ssl_context(self, tmp_path):
        v = _run(tmp_path, "http.py", "ctx = ssl._create_unverified_context()\n", "python")
        assert v and v[0]["severity"] == "high"

    def test_detects_non_constant_time_comparison(self, tmp_path):
        v = _run(tmp_path, "auth.py", "if password == provided:\n    pass\n", "python")
        assert any("timing attacks" in x["message"] for x in v)

    def test_strong_primitives_are_clean(self, tmp_path):
        code = (
            "import hashlib, secrets, hmac\n"
            "digest = hashlib.sha256(data).hexdigest()\n"
            "nonce = secrets.token_hex(16)\n"
            "ok = hmac.compare_digest(a, b)\n"
            "requests.get(url, timeout=5)\n"
        )
        assert _run(tmp_path, "safe.py", code, "python") == []


class TestCSharpChecks:
    def test_detects_md5_create(self, tmp_path):
        v = _run(tmp_path, "Hash.cs", "var h = MD5.Create();\n", "csharp")
        assert any("Weak hash" in x["message"] for x in v)

    def test_detects_obsolete_cipher(self, tmp_path):
        v = _run(tmp_path, "Cipher.cs", "var des = new TripleDESCryptoServiceProvider();\n", "csharp")
        assert any("Obsolete symmetric cipher" in x["message"] for x in v)

    def test_detects_ecb_mode(self, tmp_path):
        v = _run(tmp_path, "Cipher.cs", "aes.Mode = CipherMode.ECB;\n", "csharp")
        assert any("ECB mode" in x["message"] for x in v)

    def test_detects_system_random(self, tmp_path):
        v = _run(tmp_path, "Token.cs", "var rng = new Random();\n", "csharp")
        assert any("unguessable" in x["message"] for x in v)

    def test_detects_certificate_callback_override(self, tmp_path):
        code = "handler.ServerCertificateCustomValidationCallback = (a, b, c, d) => true;\n"
        v = _run(tmp_path, "Client.cs", code, "csharp")
        assert any("certificate validation disabled" in x["message"] for x in v)

    def test_strong_primitives_are_clean(self, tmp_path):
        code = "using var sha = SHA256.Create();\nvar bytes = RandomNumberGenerator.GetBytes(32);\n"
        assert _run(tmp_path, "Safe.cs", code, "csharp") == []


class TestGoChecks:
    def test_detects_md5_import(self, tmp_path):
        v = _run(tmp_path, "hash.go", 'import "crypto/md5"\n', "go")
        assert any("Weak hash" in x["message"] for x in v)

    def test_detects_math_rand(self, tmp_path):
        v = _run(tmp_path, "tok.go", "n := rand.Intn(1000)\n", "go")
        assert any("unguessable" in x["message"] for x in v)

    def test_detects_insecure_skip_verify(self, tmp_path):
        v = _run(tmp_path, "client.go", "tls.Config{InsecureSkipVerify: true}\n", "go")
        assert v and v[0]["severity"] == "high"

    def test_secure_code_is_clean(self, tmp_path):
        code = 'import "crypto/sha256"\nh := sha256.New()\n'
        assert _run(tmp_path, "safe.go", code, "go") == []


class TestJavaScriptChecks:
    def test_detects_md5_hash(self, tmp_path):
        v = _run(tmp_path, "hash.js", "const h = crypto.createHash('md5');\n", "javascript")
        assert any("Weak hash" in x["message"] for x in v)

    def test_detects_math_random(self, tmp_path):
        v = _run(tmp_path, "tok.js", "const id = Math.random().toString(36);\n", "javascript")
        assert any("unguessable" in x["message"] for x in v)

    def test_detects_reject_unauthorized_false(self, tmp_path):
        v = _run(tmp_path, "agent.js", "new https.Agent({ rejectUnauthorized: false });\n", "javascript")
        assert v and v[0]["severity"] == "high"

    def test_typescript_shares_javascript_rules(self, tmp_path):
        v = _run(tmp_path, "tok.ts", "const id: string = Math.random().toString();\n", "typescript")
        assert any("unguessable" in x["message"] for x in v)


class TestShellChecks:
    def test_detects_powershell_skip_certificate_check(self, tmp_path):
        v = _run(tmp_path, "get.ps1", "Invoke-RestMethod -Uri $u -SkipCertificateCheck\n", "powershell")
        assert any("certificate validation disabled" in x["message"] for x in v)

    def test_detects_powershell_weak_file_hash(self, tmp_path):
        v = _run(tmp_path, "hash.ps1", "Get-FileHash -Path $p -Algorithm MD5\n", "powershell")
        assert any("Weak hash" in x["message"] for x in v)

    def test_detects_curl_insecure(self, tmp_path):
        v = _run(tmp_path, "fetch.sh", "curl -k https://internal/api\n", "bash")
        assert any("certificate validation disabled" in x["message"] for x in v)

    def test_detects_md5sum(self, tmp_path):
        v = _run(tmp_path, "verify.sh", "md5sum release.tar.gz\n", "bash")
        assert any("MD5 used for integrity" in x["message"] for x in v)

    def test_verified_download_is_clean(self, tmp_path):
        assert _run(tmp_path, "safe.sh", "curl https://x/a\nsha256sum a\n", "bash") == []
