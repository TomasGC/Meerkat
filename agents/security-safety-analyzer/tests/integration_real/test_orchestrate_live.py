"""orchestrate.py end to end against the live local AI server — full pipeline via subprocess.

The security checker's AI pass analyzes every fixture file, so a run takes minutes; with the model
offloaded to CPU, over ten. It lived in the mock tier until #36, where it hung the CI-safe run.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ssa.model_utils import check_server_available

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(not check_server_available(), reason="local AI server not reachable"),
]

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
# A slow model fails the test instead of hanging the session.
_TIMEOUT_S = 1800

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
    """Run orchestrate.py to completion, at most _TIMEOUT_S seconds."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"),
         "--path", str(src), "--checks", checks,
         "--format", fmt, "--no-cache", "--full"],
        capture_output=True, text=True, timeout=_TIMEOUT_S,
    )


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
