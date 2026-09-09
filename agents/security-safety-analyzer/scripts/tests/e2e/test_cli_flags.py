"""E2E tests for output-shaping CLI flags — filtering, limiting, file output.

Uses error_handling only: it is purely mechanical, so these run without a
local AI server and stay deterministic.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent

MIXED_SEVERITY_PYTHON = """\
def swallow():
    try:
        risky()
    except Exception:
        pass

def broad():
    try:
        risky()
    except:
        handle()
"""


@pytest.fixture
def src(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text(MIXED_SEVERITY_PYTHON)
    return src_dir


def _run(src_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"),
         "--path", str(src_dir), "--checks", "error_handling",
         "--format", "json", "--no-cache", "--full", *extra],
        capture_output=True, text=True,
    )


def test_min_severity_high_keeps_only_high(src):
    result = _run(src, "--min-severity", "high")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["violations"], "fixture must produce at least one high violation"
    assert {v["severity"] for v in data["violations"]} == {"high"}


def test_min_severity_low_keeps_everything(src):
    strict = json.loads(_run(src, "--min-severity", "high").stdout)
    loose = json.loads(_run(src, "--min-severity", "low").stdout)
    assert len(loose["violations"]) >= len(strict["violations"])


def test_top_limits_reported_violations(src):
    result = _run(src, "--top", "1")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert len(data["violations"]) == 1


def test_violations_sorted_by_severity(src):
    data = json.loads(_run(src).stdout)
    order = {"high": 0, "medium": 1, "low": 2}
    ranks = [order[v["severity"]] for v in data["violations"]]
    assert ranks == sorted(ranks)


def test_output_flag_writes_json_file(src, tmp_path):
    target = tmp_path / "report.json"
    result = _run(src, "--output", str(target))
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "violations" in data
    assert "total_violations" in data


def test_staged_on_non_git_path_still_exits_zero(src):
    """Git helpers return None outside a repo; the run must fall back, not crash."""
    result = _run(src, "--staged")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    json.loads(result.stdout)


def test_since_on_non_git_path_still_exits_zero(src):
    result = _run(src, "--since", "HEAD~1")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    json.loads(result.stdout)
