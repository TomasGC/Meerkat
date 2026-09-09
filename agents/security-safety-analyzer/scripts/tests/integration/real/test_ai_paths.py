"""Live-AI tests for the checkers that call a model.

These exercise the path that mocked tests cannot: real prompt rendering, real
response parsing, and the mechanical/AI reconciliation. Skipped when no local
AI server is reachable.
"""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.model_utils import check_server_available

pytestmark = pytest.mark.skipif(
    not check_server_available("fast"),
    reason="local AI server not reachable",
)

VULNERABLE_PYTHON = """\
import subprocess

API_KEY = "sk-live-abc123def456"


def get_user(cur, user_id):
    cur.execute("SELECT * FROM users WHERE id = " + user_id)
    return cur.fetchone()


def run_cmd(user_cmd):
    return subprocess.run(user_cmd, shell=True)
"""

AGENT_PYTHON = """\
def build_prompt(user_message, client):
    prompt = f"You are a helpful assistant. Answer: {user_message}"
    return client.complete(prompt)
"""

RACY_GO = """\
package main

var counter int

func Bump() {
\tgo func() {
\t\tcounter++
\t}()
}
"""


@pytest.fixture
def python_project(tmp_path):
    (tmp_path / "vuln.py").write_text(VULNERABLE_PYTHON)
    return tmp_path


@pytest.fixture
def agent_project(tmp_path):
    (tmp_path / "agent.py").write_text(AGENT_PYTHON)
    return tmp_path


@pytest.fixture
def go_project(tmp_path):
    (tmp_path / "worker.go").write_text(RACY_GO)
    return tmp_path


def _run(module_name: str, path: Path, language: str) -> dict:
    mod = importlib.import_module(f"checkers.{module_name}")
    return mod.run(path, language, no_cache=True)


def test_security_produces_ai_findings(python_project):
    """Security checker returns AI findings on top of mechanical ones."""
    result = _run("check_security", python_project, "python")
    assert result["success"]
    messages = [v["message"] for v in result["violations"]]
    assert any(m.startswith("[") for m in messages), f"no AI findings in {messages}"


def test_security_does_not_duplicate_mechanical_findings(python_project):
    """AI findings within three lines of a mechanical one are dropped."""
    result = _run("check_security", python_project, "python")
    by_line: dict[int, list[str]] = {}
    for violation in result["violations"]:
        by_line.setdefault(violation["line"], []).append(violation["message"])

    mechanical_lines = [
        line for line, msgs in by_line.items()
        if any(not m.startswith("[") for m in msgs)
    ]
    for line in mechanical_lines:
        near_ai = [
            other for other, msgs in by_line.items()
            if abs(other - line) <= 3 and any(m.startswith("[") for m in msgs)
        ]
        assert not near_ai, f"AI finding at {near_ai} duplicates mechanical finding at line {line}"


def test_prompt_injection_produces_findings(agent_project):
    """Prompt injection checker detects the interpolated user message."""
    result = _run("check_prompt_injection", agent_project, "python")
    assert result["success"]
    assert result["violations"]


def test_concurrency_produces_ai_findings(go_project):
    """Concurrency checker is AI-only and must return findings for a real race."""
    result = _run("check_concurrency", go_project, "go")
    assert result["success"]
    assert result["violations"]


def test_crash_bugs_ai_path_on_non_python(go_project):
    """Crash bugs uses the AI path for non-Python files without error."""
    result = _run("check_crash_bugs", go_project, "go")
    assert result["success"]
    assert result["files_analyzed"] == 1


def test_no_checker_reports_failure(python_project):
    """Every AI-capable checker completes without setting an error."""
    for module_name in ("check_security", "check_prompt_injection",
                        "check_crash_bugs", "check_concurrency"):
        result = _run(module_name, python_project, "python")
        assert result["success"], f"{module_name}: {result.get('error')}"
        assert "error" not in result
