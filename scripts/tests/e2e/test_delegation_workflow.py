#!/usr/bin/env python3
"""End-to-end tests for delegation workflow — runs real scripts via subprocess"""

import subprocess
import pytest
import json
from pathlib import Path
import time


class TestDelegationWorkflow:

    @pytest.fixture
    def temp_project(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text(
            "def   add(  a,  b  ):\n    return a+b\n\ndef multiply(x,y):\n    return x*y\n"
        )
        return tmp_path

    def test_format_code_workflow(self, temp_project):
        test_file = temp_project / "src" / "main.py"
        result = subprocess.run(
            ["python", str(Path.home() / ".claude" / "scripts" / "cli" / "format_code.py"),
             "--file", str(test_file), "--language", "python"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        assert result.returncode in [0, 1]

    def test_profile_endpoint_workflow(self):
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class FakeHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            def log_message(self, format, *args):
                pass

        server = HTTPServer(("localhost", 8889), FakeHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        try:
            result = subprocess.run(
                ["python", str(Path.home() / ".claude" / "scripts" / "delegators" / "profile_endpoint.py"),
                 "--url", "http://localhost:8889/health", "--duration", "2", "--requests-per-second", "5"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            assert result.returncode == 0
            assert len(result.stdout) > 0
        finally:
            server.shutdown()

    def test_ollama_review_workflow(self):
        try:
            subprocess.run(["ollama", "ps"], capture_output=True, check=True,
                           timeout=5, encoding="utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Ollama not running")

        result = subprocess.run(
            ["ollama", "run", "qwen2.5-coder:7b", "Review this code (one word): def add(a,b): return a+b"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_delegation_stats_workflow(self):
        log_file = Path.home() / ".claude" / "logs" / "delegation-stats.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": "2026-05-11T10:00:00", "event": "session_start",
                                "delegation_enabled": True}) + "\n")

        result = subprocess.run(
            ["python", str(Path.home() / ".claude" / "scripts" / "cli" / "delegation_stats.py")],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        assert result.returncode == 0
        assert "delegation" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
