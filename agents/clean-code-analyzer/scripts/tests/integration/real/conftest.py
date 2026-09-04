"""Conftest for real-Ollama integration tests — skip if Ollama not running."""

import http.client
import pytest


def _ollama_running() -> bool:
    try:
        conn = http.client.HTTPConnection("localhost", 11434, timeout=3)
        conn.request("GET", "/api/tags")
        return conn.getresponse().status == 200
    except Exception:
        return False


ollama_skip = pytest.mark.skipif(
    not _ollama_running(),
    reason="Ollama not running on localhost:11434",
)
