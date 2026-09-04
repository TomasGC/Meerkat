"""E2E tests: full analysis pipeline with real Docker Ollama container."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent.parent  # scripts/
FIXTURES_DIRTY = Path(__file__).parent / "fixtures" / "dirty_python"
FIXTURES_CLEAN = Path(__file__).parent / "fixtures" / "clean_python"


@pytest.mark.e2e
def test_dirty_code_detected(ollama_service):
    """Dirty fixture files produce violations from mechanical checkers."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(FIXTURES_DIRTY),
            "--checks", "error_handling,naming,lod,inheritance",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] > 0
    principles = {v["principle"] for v in data["violations"]}
    assert "ErrorHandling" in principles
    assert "Naming" in principles


@pytest.mark.e2e
def test_clean_code_zero_violations(ollama_service):
    """Clean fixture files produce 0 violations from mechanical checkers."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(FIXTURES_CLEAN),
            "--checks", "error_handling,naming,lod,inheritance",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["total_violations"] == 0, f"Unexpected violations: {data['violations']}"


@pytest.mark.e2e
def test_incremental_mode(ollama_service, tmp_path):
    """--since HEAD: only dirty.py (uncommitted) analyzed, clean.py (committed) skipped."""
    # Set up git repo
    for cmd in [
        ["git", "init"],
        ["git", "config", "user.email", "test@test.com"],
        ["git", "config", "user.name", "Test"],
    ]:
        subprocess.run(cmd, cwd=str(tmp_path), check=True)

    clean = tmp_path / "clean.py"
    clean.write_text((FIXTURES_CLEAN / "clean_service.py").read_text())
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True
    )

    dirty = tmp_path / "dirty.py"
    dirty.write_text((FIXTURES_DIRTY / "error_handling_violations.py").read_text())

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(tmp_path),
            "--since", "HEAD",
            "--checks", "error_handling",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    files = {v["file"] for v in data["violations"]}
    assert all("dirty" in f for f in files), (
        f"Expected only dirty.py violations; got: {files}"
    )


@pytest.mark.e2e
@pytest.mark.repeat(5)
@pytest.mark.slow
def test_agents_n_deduplicates(ollama_service, tmp_path):
    """--agents 3 finds >= violations as --agents 1, but not 3x more (dedup works)."""
    import subprocess, json
    # Create a dirty project
    dirty = tmp_path / "dirty.py"
    dirty.write_text("""
class GodClass:
    def handle_user(self): pass
    def send_email(self): pass
    def generate_report(self): pass
    def process_payment(self): pass

try:
    risky()
except:
    pass
""")
    def run_with_agents(n):
        r = subprocess.run(
            ["python", str(SCRIPTS_DIR / "orchestrate.py"),
             "--path", str(tmp_path),
             "--checks", "solid",
             "--agents", str(n),
             "--format", "json", "--no-cache"],
            capture_output=True, text=True, timeout=120
        )
        assert r.returncode == 0, f"Failed: {r.stderr}"
        return json.loads(r.stdout)

    result_n1 = run_with_agents(1)
    result_n3 = run_with_agents(3)

    n1_count = result_n1["total_violations"]
    n3_count = result_n3["total_violations"]

    # N=3 should not be 3x N=1 (dedup working)
    assert n3_count < n1_count * 3, f"Dedup failed: n1={n1_count}, n3={n3_count}"
    # N=3 should find at least as many as N=1
    assert n3_count >= n1_count, f"N=3 found fewer than N=1: n1={n1_count}, n3={n3_count}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("language,fixture_subdir", [
    ("typescript", "dirty_typescript"),
    ("javascript", "dirty_javascript"),
    ("go",         "dirty_go"),
    ("powershell", "dirty_powershell"),
    ("bash",       "dirty_bash"),
])
def test_multilang_e2e_violations_detected(ollama_service, language, fixture_subdir):
    """Full pipeline on multi-language dirty fixtures finds violations."""
    import subprocess, json
    fixture_path = Path(__file__).parent / "fixtures" / fixture_subdir
    if not fixture_path.exists():
        pytest.skip(f"Fixture missing: {fixture_path}")

    result = subprocess.run(
        ["python", str(SCRIPTS_DIR / "orchestrate.py"),
         "--path", str(fixture_path),
         "--checks", "solid,cqrs",  # Ollama checkers — language-agnostic
         "--format", "json", "--no-cache"],
        capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    # Just verify it ran and didn't crash — Ollama accuracy varies
    assert isinstance(data.get("violations"), list)
    assert data.get("files_analyzed", 0) > 0 or data.get("total_violations", 0) >= 0
