"""Integration tests for orchestrate.py — full pipeline via subprocess.

No timeout: process exit is the completion signal. With a local AI server up
these run for minutes, since the AI checkers analyze every fixture file.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent

DIRTY_PYTHON = """\
import os
password = 'hardcoded_secret_123'

def process(user_input):
    result = 10 / user_input
    try:
        risky()
    except:
        pass
    return result

x = obj.service.repo.find_by_id(42)
"""

CLEAN_PYTHON = """\
SECONDS_PER_DAY = 86400

class UserService:
    def __init__(self, repo):
        self._repo = repo

    def get_user(self, user_id: int):
        return self._repo.find_by_id(user_id)
"""


def _run_orchestrate(src: Path, checks: str, fmt: str) -> subprocess.CompletedProcess:
    """Run orchestrate.py to completion. Process exit is the event; no timeout."""
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"),
         "--path", str(src), "--checks", checks,
         "--format", fmt, "--no-cache", "--full"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    stdout, stderr = proc.communicate()
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


@pytest.fixture
def dirty_src(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(DIRTY_PYTHON)
    return src


@pytest.fixture
def clean_src(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(CLEAN_PYTHON)
    return src


def test_full_pipeline_produces_violations(dirty_src):
    result = _run_orchestrate(dirty_src, "security,error_handling", "json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] > 0
    principles = {v["principle"] for v in data["violations"]}
    assert "Security" in principles or "ErrorHandling" in principles


def test_clean_source_no_mechanical_violations(clean_src):
    result = _run_orchestrate(clean_src, "error_handling", "json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] == 0


def test_format_table_exits_zero(dirty_src):
    result = _run_orchestrate(dirty_src, "security,error_handling", "table")
    assert result.returncode == 0
    assert "Security Safety Analysis" in result.stdout or "SEVERITY" in result.stdout


def test_unknown_checker_warns_and_continues(dirty_src):
    result = _run_orchestrate(dirty_src, "security,nonexistent_checker", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "nonexistent_checker" in result.stderr or data["checkers_run"] == 1
