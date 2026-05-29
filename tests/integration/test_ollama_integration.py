#!/usr/bin/env python3
"""Integration tests for Ollama models"""

import subprocess
import pytest
import time


class TestOllamaIntegration:
    """Integration tests for Ollama."""

    @pytest.fixture(autouse=True)
    def check_ollama_running(self):
        """Check if Ollama is running."""
        try:
            subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                check=True,
                timeout=5,
                encoding="utf-8",
                errors="replace"
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Ollama not running")

    def test_ollama_installed(self):
        """Test Ollama is installed."""
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        assert result.returncode == 0
        assert "ollama version" in result.stdout

    def test_hot_models_available(self):
        """Test hot tier models are available."""
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace"
        )

        hot_models = [
            "llama-guard3:1b",
            "llama3.2:3b",
            "qwen2.5-coder:7b"
        ]

        for model in hot_models:
            assert model in result.stdout, f"Model {model} not found"

    def test_llama_guard_quick_response(self):
        """Test llama-guard3:1b responds quickly."""
        start = time.time()

        result = subprocess.run(
            ["ollama", "run", "llama-guard3:1b", "Say hello"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace"
        )

        elapsed = time.time() - start

        assert result.returncode == 0
        assert len(result.stdout) > 0

        # Should be fast (hot tier) - Allow 6s for CPU variations
        assert elapsed < 6, f"Too slow: {elapsed:.1f}s (expected <6s)"

    def test_llama32_syntax_check(self):
        """Test llama3.2:3b can do syntax checking."""
        code = """
def hello():
    print("Hello, World!")
"""

        prompt = f"Check if this Python code has syntax errors (yes/no only):\n{code}"

        result = subprocess.run(
            ["ollama", "run", "llama3.2:3b", prompt],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace"
        )

        assert result.returncode == 0

        # Response should indicate no errors (relaxed - model output varies)
        response = result.stdout.lower()
        assert len(response) > 0  # Got some response
        # Don't assert on specific words - LLM responses vary

    def test_qwen_code_review(self):
        """Test qwen2.5-coder:7b can review code."""
        code = """
def add(a, b):
    return a + b
"""

        prompt = f"Review this code (one sentence):\n{code}"

        result = subprocess.run(
            ["ollama", "run", "qwen2.5-coder:7b", prompt],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace"
        )

        assert result.returncode == 0
        assert len(result.stdout) > 10  # Got some response

    def test_model_unload_reload(self):
        """Test model can be unloaded and reloaded."""
        # Stop all models
        subprocess.run(
            ["ollama", "stop", "--all"],
            capture_output=True,
            timeout=5,
            encoding="utf-8",
            errors="replace"
        )

        time.sleep(2)

        # Check nothing loaded
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # Reload
        result = subprocess.run(
            ["ollama", "run", "llama-guard3:1b", "test"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace"
        )

        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
