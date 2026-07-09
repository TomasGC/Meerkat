#!/usr/bin/env python3
"""Integration tests for Ollama models — requires live Ollama"""

import subprocess
import pytest
import time


class TestOllamaIntegration:

    @pytest.fixture(autouse=True)
    def check_ollama_running(self):
        try:
            subprocess.run(["ollama", "ps"], capture_output=True, check=True,
                           timeout=5, encoding="utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Ollama not running")

    def test_ollama_installed(self):
        result = subprocess.run(["ollama", "--version"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        assert result.returncode == 0
        assert "ollama version" in result.stdout

    def test_hot_models_available(self):
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                                check=True, encoding="utf-8", errors="replace")
        for model in ["llama-guard3:1b", "llama3.2:3b", "qwen2.5-coder:7b"]:
            assert model in result.stdout, f"Model {model} not found"

    def test_llama_guard_quick_response(self):
        start = time.time()
        result = subprocess.run(["ollama", "run", "llama-guard3:1b", "Say hello"],
                                capture_output=True, text=True, timeout=10,
                                encoding="utf-8", errors="replace")
        elapsed = time.time() - start
        assert result.returncode == 0
        assert len(result.stdout) > 0
        assert elapsed < 6, f"Too slow: {elapsed:.1f}s"

    def test_llama32_syntax_check(self):
        result = subprocess.run(
            ["ollama", "run", "llama3.2:3b",
             "Check if this Python code has syntax errors (yes/no only):\ndef hello():\n    print('Hello')"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace"
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_qwen_code_review(self):
        result = subprocess.run(
            ["ollama", "run", "qwen2.5-coder:7b",
             "Review this code (one sentence):\ndef add(a, b):\n    return a + b"],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace"
        )
        assert result.returncode == 0
        assert len(result.stdout) > 10

    def test_model_unload_reload(self):
        subprocess.run(["ollama", "stop", "--all"], capture_output=True,
                       timeout=5, encoding="utf-8", errors="replace")
        time.sleep(2)
        result = subprocess.run(["ollama", "run", "llama-guard3:1b", "test"],
                                capture_output=True, text=True, timeout=15,
                                encoding="utf-8", errors="replace")
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
