"""E2E conftest — starts/stops Docker Ollama container for the test session."""

import http.client
import subprocess
import time
from pathlib import Path

import pytest

E2E_DIR = Path(__file__).parent


def _docker_available() -> bool:
    try:
        return subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        ).returncode == 0
    except Exception:
        return False


def _ollama_up() -> bool:
    try:
        conn = http.client.HTTPConnection("localhost", 11434, timeout=3)
        conn.request("GET", "/api/tags")
        return conn.getresponse().status == 200
    except Exception:
        return False


requires_docker = pytest.mark.skipif(
    not _docker_available(), reason="Docker not available"
)


@pytest.fixture(scope="session")
def ollama_service():
    """Session-scoped fixture: spin up Ollama via docker-compose, yield, tear down."""
    if not _docker_available():
        pytest.skip("Docker not available")

    compose = E2E_DIR / "docker-compose.yml"
    subprocess.run(
        ["docker-compose", "-f", str(compose), "up", "-d"],
        check=True,
        timeout=60,
    )

    # Wait up to 3 minutes for Ollama to become healthy
    for _ in range(36):
        if _ollama_up():
            break
        time.sleep(5)
    else:
        pytest.fail("Ollama container did not become healthy after 3 minutes")

    # Pull the model used by checkers
    subprocess.run(
        ["docker", "exec", "cca-ollama", "ollama", "pull", "qwen2.5-coder:7b"],
        check=True,
        timeout=300,
    )

    yield

    subprocess.run(
        ["docker-compose", "-f", str(compose), "down"],
        timeout=30,
    )
