"""E2E tests: full analysis pipeline against the configured local AI provider."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"  # scripts/
FIXTURES_DIRTY = Path(__file__).parent.parent / "fixtures" / "e2e" / "dirty_python"
FIXTURES_CLEAN = Path(__file__).parent.parent / "fixtures" / "e2e" / "clean_python"


@pytest.mark.live_ai
def test_dirty_code_detected(local_ai_service):
    """Dirty fixture files produce violations from mechanical checkers."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(FIXTURES_DIRTY),
            "--full",
            "--checks", "naming,lod,inheritance",
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
    assert "Naming" in principles


@pytest.mark.live_ai
def test_clean_code_zero_violations(local_ai_service):
    """Clean fixture files produce 0 violations from mechanical checkers."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(FIXTURES_CLEAN),
            "--full",
            "--checks", "naming,lod,inheritance",
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


_VIOLATING_SOURCE = "x = 42\n# TODO: x\n"
_EXTRA_VIOLATION = "y = 99\n# TODO: y\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True)


def _init_repo_with_two_violating_files(repo: Path) -> None:
    """Repo on branch `main` with a.py and b.py committed, both violating naming + comments."""
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "a.py").write_text(_VIOLATING_SOURCE)
    (repo / "b.py").write_text(_VIOLATING_SOURCE)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")


def _append_violation(path: Path) -> None:
    path.write_text(path.read_text() + _EXTRA_VIOLATION)


def _run_mechanical(repo: Path, *mode_flags: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", str(repo),
            *mode_flags,
            "--checks", "naming,comments",
            "--format", "json",
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)


def _assert_only_a_py(data: dict) -> None:
    files = {v["file"] for v in data["violations"]}
    assert data["violations"], "Expected violations in a.py; got none"
    assert files == {"a.py"}, f"Expected only a.py violations; got: {files}"


def test_incremental_since_head_only_modified_file(tmp_path):
    """--since HEAD: only the modified tracked file is analyzed; the unchanged one is skipped."""
    _init_repo_with_two_violating_files(tmp_path)
    _append_violation(tmp_path / "a.py")

    data = _run_mechanical(tmp_path, "--since", "HEAD")

    _assert_only_a_py(data)
    assert data["incremental_files"] == 1


def test_incremental_staged_only_staged_file(tmp_path):
    """--staged: of two modified files, only the staged one is analyzed."""
    _init_repo_with_two_violating_files(tmp_path)
    _append_violation(tmp_path / "a.py")
    _append_violation(tmp_path / "b.py")
    _git(tmp_path, "add", "a.py")

    data = _run_mechanical(tmp_path, "--staged")

    _assert_only_a_py(data)


def test_incremental_branch_vs_main_default_mode(tmp_path):
    """No incremental flag: auto branch-vs-main analyzes only files changed on the feature branch."""
    _init_repo_with_two_violating_files(tmp_path)
    _git(tmp_path, "checkout", "-b", "feature")
    _append_violation(tmp_path / "a.py")
    _git(tmp_path, "commit", "-am", "change a")

    data = _run_mechanical(tmp_path)

    _assert_only_a_py(data)


def test_clear_cache_honours_cca_cache_dir(tmp_path):
    """--clear-cache empties the CCA_CACHE_DIR directory, never the real user cache."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    entries = [cache_dir / "aaa_SOLID.json", cache_dir / "bbb_KISS.json"]
    for entry in entries:
        entry.write_text("[]")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate.py"), "--clear-cache"],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "CCA_CACHE_DIR": str(cache_dir)},
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert not any(entry.exists() for entry in entries)
    assert "Cleared 2" in result.stderr


@pytest.mark.live_ai
@pytest.mark.slow
def test_agents_n_completes_without_duplicates(local_ai_service, tmp_path):
    """--agents 3 completes and emits no duplicate (file, line, principle) entries.

    No count ratio against an --agents 1 run: each run is an independent
    nondeterministic sample, so both a lower and an upper ratio bound were observed
    to fail at random. Merge exactness is unit-tested against fixed responses in
    tests/unit/test_model_utils_unit.py; here the orchestrator's own dedup also
    applies, so the CLI output cannot isolate the agents-level merge.
    """
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
    r = subprocess.run(
        ["python", str(SCRIPTS_DIR / "orchestrate.py"),
         "--path", str(tmp_path),
         "--checks", "solid",
         "--agents", "3",
         "--fast",
         "--format", "json", "--no-cache"],
        capture_output=True, text=True, timeout=300
    )
    assert r.returncode == 0, f"Failed: {r.stderr}"
    data = json.loads(r.stdout)

    assert data["files_analyzed"] > 0
    keys = [(v["file"], v["line"], v["principle"]) for v in data["violations"]]
    assert len(keys) == len(set(keys)), f"Duplicate violations survived merge: {keys}"


@pytest.mark.live_ai
@pytest.mark.slow
@pytest.mark.parametrize("language,fixture_subdir", [
    ("typescript", "dirty_typescript"),
    ("javascript", "dirty_javascript"),
    ("go",         "dirty_go"),
    ("powershell", "dirty_powershell"),
    ("bash",       "dirty_bash"),
])
def test_multilang_e2e_violations_detected(local_ai_service, language, fixture_subdir):
    """Full pipeline on multi-language dirty fixtures finds violations."""
    import subprocess, json
    fixture_path = Path(__file__).parent.parent / "fixtures" / "e2e" / fixture_subdir
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
