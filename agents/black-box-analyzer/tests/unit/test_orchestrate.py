#!/usr/bin/env python3
"""Tests for bba/orchestrate.py and its scripts/orchestrate.py wrapper — unit tests (git and the pipeline
subprocess mocked)"""

import json
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from bba import orchestrate

_WRAPPER = Path(__file__).resolve().parents[2] / "scripts" / "orchestrate.py"


def _completed(returncode=0, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_gaps_cache_dir_lives_under_bba_cache_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BBA_CACHE_DIR", str(tmp_path))
    assert orchestrate._gaps_cache_dir() == tmp_path / "gaps"


def test_detect_base_branch_prefers_main():
    with patch.object(orchestrate.subprocess, "run", return_value=_completed(0)) as run:
        assert orchestrate._detect_base_branch(Path(".")) == "main"
    assert run.call_count == 1


def test_detect_base_branch_falls_back_to_master():
    with patch.object(orchestrate.subprocess, "run", side_effect=[_completed(1), _completed(0)]):
        assert orchestrate._detect_base_branch(Path(".")) == "master"


def test_detect_base_branch_none_when_neither_exists():
    with patch.object(orchestrate.subprocess, "run", return_value=_completed(128)):
        assert orchestrate._detect_base_branch(Path(".")) is None


def test_get_branch_files_keeps_only_existing_files(tmp_path):
    (tmp_path / "kept.py").write_text("x")
    stdout = "kept.py\n\ndeleted.py\n"
    with patch.object(orchestrate.subprocess, "run", return_value=_completed(0, stdout)):
        assert orchestrate._get_branch_files(tmp_path, "main") == [tmp_path / "kept.py"]


def test_get_branch_files_none_when_all_deleted(tmp_path):
    with patch.object(orchestrate.subprocess, "run", return_value=_completed(0, "gone.py\n")):
        assert orchestrate._get_branch_files(tmp_path, "main") is None


def test_get_branch_files_none_on_git_failure(tmp_path):
    with patch.object(orchestrate.subprocess, "run", return_value=_completed(128)):
        assert orchestrate._get_branch_files(tmp_path, "main") is None


def test_main_gaps_delegates_to_engine_without_the_flag():
    with patch("lib.engine.orchestrator.main") as engine_main:
        orchestrate.main(["--gaps", "--path", "x", "--full"])
    kwargs = engine_main.call_args.kwargs
    assert kwargs["argv"] == ["--path", "x", "--full"]
    assert kwargs["registry"] == orchestrate.CHECKERS
    assert kwargs["max_workers"] == 4
    assert kwargs["cache_dir"] == orchestrate._gaps_cache_dir()


def test_main_clear_cache_reports_count_and_returns(capsys):
    with patch.object(orchestrate, "clear_model_cache", return_value=2), patch.object(
        orchestrate, "clear_cache", return_value=3
    ), patch.object(orchestrate, "AnalysisCache") as cache_cls, patch.object(orchestrate.subprocess, "run") as run:
        orchestrate.main(["--clear-cache"])
    assert "Cleared 5 cached result(s)." in capsys.readouterr().out
    cache_cls.return_value.invalidate_all.assert_called_once_with(include_projects=True)
    run.assert_not_called()


def _run_pipeline(argv, git_base=None, branch_files=None):
    """Run main() with git helpers stubbed; return the pipeline subprocess call."""
    with patch.object(orchestrate, "_detect_base_branch", return_value=git_base), patch.object(
        orchestrate, "_get_branch_files", return_value=branch_files
    ), patch.object(orchestrate.subprocess, "run", return_value=_completed(7)) as run:
        with pytest.raises(SystemExit) as exc:
            orchestrate.main(argv)
    return run, exc.value.code


def test_main_full_runs_pipeline_with_role_and_flags(tmp_path):
    out = tmp_path / "r.json"
    run, code = _run_pipeline(["--path", str(tmp_path), "--full", "--fast", "--no-cache", "--output", str(out)])

    assert code == 7
    cmd = run.call_args.args[0]
    assert cmd[1].endswith("parallel_analyzer.py")
    assert cmd[2] == str(tmp_path.resolve())
    assert "--no-cache" in cmd
    assert cmd[cmd.index("--output") + 1] == str(out)
    env = run.call_args.kwargs["env"]
    assert env["BBA_ROLE"] == "fast"
    assert env["BBA_AGENTS"] == "1"
    assert "BBA_FILES" not in env


def test_main_role_overrides_fast(tmp_path):
    run, _ = _run_pipeline(["--path", str(tmp_path), "--full", "--fast", "--role", "deep", "--agents", "3"])
    env = run.call_args.kwargs["env"]
    assert env["BBA_ROLE"] == "deep"
    assert env["BBA_AGENTS"] == "3"


def test_main_incremental_passes_changed_files(tmp_path, capsys):
    changed = [tmp_path / "a.py"]
    run, _ = _run_pipeline(["--path", str(tmp_path)], git_base="main", branch_files=changed)

    assert json.loads(run.call_args.kwargs["env"]["BBA_FILES"]) == [str(changed[0])]
    assert "Incremental mode: 1 changed file(s) vs main" in capsys.readouterr().err


def test_main_incremental_without_changes_runs_nothing(tmp_path, capsys):
    with patch.object(orchestrate, "_detect_base_branch", return_value="main"), patch.object(
        orchestrate, "_get_branch_files", return_value=None
    ), patch.object(orchestrate.subprocess, "run") as run:
        orchestrate.main(["--path", str(tmp_path)])
    run.assert_not_called()
    assert "nothing to analyze" in capsys.readouterr().err


def test_main_without_base_branch_falls_back_to_full(tmp_path, capsys):
    run, _ = _run_pipeline(["--path", str(tmp_path)], git_base=None)
    assert "BBA_FILES" not in run.call_args.kwargs["env"]
    assert "falling back to full analysis" in capsys.readouterr().err


def test_wrapper_runs_bba_orchestrate_main(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(_WRAPPER), "--clear-cache"])
    runpy.run_path(str(_WRAPPER), run_name="__main__")
    assert "Cleared" in capsys.readouterr().out
