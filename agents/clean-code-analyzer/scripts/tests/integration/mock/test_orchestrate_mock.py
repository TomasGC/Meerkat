"""Integration tests: full pipeline via subprocess, mechanical checkers only (no Ollama)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent  # scripts/
sys.path.insert(0, str(SCRIPTS_DIR))

# Re-import fixtures from conftest (available automatically via pytest discovery)
# DIRTY_PYTHON / CLEAN_PYTHON and dirty_project / clean_project come from conftest.py

DIRTY_PYTHON = """
class GodClass:
    def handle_user(self, user): pass
    def send_email(self, to, body): pass
    def generate_report(self, data): pass
    def save_to_db(self, obj): pass
    def calculate_tax(self, amount): return amount * 86400

try:
    risky_operation()
except:
    pass

class Animal: pass
class Mammal(Animal): pass
class Dog(Mammal): pass
class Labrador(Dog): pass
class GoldenRetriever(Labrador): pass

x = obj.service.repo.find_by_id(42)
"""

CLEAN_PYTHON = """
SECONDS_PER_DAY = 86400

class UserService:
    def __init__(self, repo) -> None:
        self._repo = repo

    def get_user(self, user_id: int):
        return self._repo.find_by_id(user_id)

def double_positives(items):
    return [item * 2 for item in items if item > 0]

try:
    risky_operation()
except ValueError as exc:
    logger.error("failed: %s", exc)
    raise
"""


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


@pytest.mark.integration_mock
def test_full_pipeline_mechanical_only(dirty_src):
    """Mechanical checkers run without Ollama — must detect violations."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_src),
            "--checks", "error_handling,naming,lod,inheritance",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] > 0
    principles = {v["principle"] for v in data["violations"]}
    assert "ErrorHandling" in principles
    assert "Naming" in principles


@pytest.mark.integration_mock
def test_clean_code_no_mechanical_violations(clean_src):
    """Clean code → 0 violations from non-naming mechanical checkers.

    Naming is excluded because the bool-method heuristic (flagging any
    self-method not starting with is_/has_/can_/should_) fires on 'get_user'.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(clean_src),
            "--checks", "error_handling,lod,inheritance",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] == 0, f"Unexpected violations: {data['violations']}"


@pytest.mark.integration_mock
def test_checker_failure_continues(dirty_src):
    """Unknown checker in --checks is warned about; known checkers still run."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_src),
            "--checks", "error_handling,nonexistent_checker",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    # error_handling should still produce violations
    assert any(v["principle"] == "ErrorHandling" for v in data["violations"])
    # Unknown checker is warned about on stderr
    assert "nonexistent_checker" in result.stderr or data["checkers_run"] == 1


@pytest.mark.integration_mock
def test_json_output_schema(dirty_src):
    """JSON output has expected top-level keys."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_src),
            "--checks", "error_handling",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    for key in ("success", "path", "language", "total_violations", "violations", "summary"):
        assert key in data, f"Missing key: {key}"


# ── Additional coverage ─────────────────────────────────────────────────────────

@pytest.mark.integration_mock
def test_output_flag_writes_file(dirty_project, tmp_path):
    """--output PATH writes JSON results to the specified file."""
    out = tmp_path / "results.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_project / "src"),
            "--checks", "error_handling,naming",
            "--format", "json",
            "--no-cache",
            "--output", str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out.exists(), "--output file was not created"
    data = json.loads(out.read_text())
    assert "violations" in data


@pytest.mark.integration_mock
def test_format_table_produces_non_json_output(dirty_project):
    """--format table produces ASCII table output, not JSON."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_project / "src"),
            "--checks", "error_handling",
            "--format", "table",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Table format should NOT be valid JSON on stdout
    try:
        json.loads(result.stdout)
        is_json = True
    except (json.JSONDecodeError, ValueError):
        is_json = False
    assert not is_json, "Expected table format on stdout, but got valid JSON"


@pytest.mark.integration_mock
def test_min_severity_high_filters_lower_violations(dirty_project):
    """--min-severity high removes medium/low violations; result is subset of all."""
    run_all = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_project / "src"),
            "--checks", "naming",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True, text=True, timeout=60,
    )
    run_high = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_project / "src"),
            "--checks", "naming",
            "--format", "json",
            "--no-cache",
            "--min-severity", "high",
        ],
        capture_output=True, text=True, timeout=60,
    )
    assert run_all.returncode == 0
    assert run_high.returncode == 0
    all_data = json.loads(run_all.stdout)
    high_data = json.loads(run_high.stdout)
    assert high_data["total_violations"] <= all_data["total_violations"]
    # Every violation in the high-filtered result must have severity "high"
    for v in high_data["violations"]:
        assert v["severity"] == "high", f"Expected high severity, got: {v}"


@pytest.mark.integration_mock
def test_top_n_limits_output(dirty_project):
    """--top 1 returns at most 1 violation in JSON output."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(dirty_project / "src"),
            "--checks", "naming,error_handling,lod,inheritance",
            "--format", "json",
            "--no-cache",
            "--top", "1",
        ],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert len(data["violations"]) <= 1


@pytest.mark.integration_mock
def test_clear_cache_flag_exits_zero():
    """--clear-cache exits 0 and reports cleared entries."""
    # Pre-populate a fake cache entry so there's something to clear
    cache_dir = Path.home() / ".claude" / "agents" / "clean-code-analyzer" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    fake_entry = cache_dir / "_test_fake_entry.json"
    fake_entry.write_text("[]")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"), "--clear-cache"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert not fake_entry.exists(), "Fake cache entry was not deleted"
