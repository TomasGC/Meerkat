#!/usr/bin/env python3
"""Tests for parallel_analyzer.py — int_mock tests (main() CLI on a real filesystem, analysis mocked)"""

import json
import sys
from unittest.mock import patch

import parallel_analyzer
import pytest
from bba.cache import AnalysisCache

_REPORT = {"success": True, "project_info": {"language": "python"}, "summary": {"total_entry_points": 0}}


def _run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["parallel_analyzer.py", *argv])
    return parallel_analyzer.main()


@pytest.fixture
def fake_router():
    with patch.object(parallel_analyzer, "AnalyzerRouter") as router_cls:
        router_cls.return_value.analyze_project.return_value = dict(_REPORT)
        yield router_cls.return_value


def test_main_writes_report_and_project_info_next_to_output(monkeypatch, tmp_path, fake_router, capsys):
    out = tmp_path / "out" / "report.json"
    out.parent.mkdir()

    code = _run_main(monkeypatch, str(tmp_path), "--output", str(out), "--verbose")

    assert code == 0
    assert json.loads(out.read_text(encoding="utf-8")) == _REPORT
    assert json.loads((out.parent / "project_info.json").read_text(encoding="utf-8")) == {"language": "python"}
    captured = capsys.readouterr()
    assert "Report written to" in captured.out
    assert "Next steps" in captured.err


def test_main_without_output_prints_report_and_writes_project_info_in_project(
    monkeypatch, tmp_path, fake_router, capsys
):
    code = _run_main(monkeypatch, str(tmp_path))

    assert code == 0
    assert json.loads(capsys.readouterr().out) == _REPORT
    assert (tmp_path / "project_info.json").exists()


def test_main_no_cache_flag_disables_cache(monkeypatch, tmp_path, fake_router, capsys):
    _run_main(monkeypatch, str(tmp_path), "--no-cache", "--max-workers", "2")

    args, kwargs = fake_router.analyze_project.call_args
    assert args[1] == 2
    assert kwargs["use_cache"] is False


def test_main_unsuccessful_report_exits_one(monkeypatch, tmp_path, fake_router, capsys):
    fake_router.analyze_project.return_value = {"success": False, "project_info": {}}
    assert _run_main(monkeypatch, str(tmp_path)) == 1


def test_main_analysis_error_exits_one(monkeypatch, tmp_path, fake_router, capsys):
    fake_router.analyze_project.side_effect = ValueError("No analyzer found for types: []")

    assert _run_main(monkeypatch, str(tmp_path)) == 1
    assert "Error: No analyzer found" in capsys.readouterr().err


def test_main_clear_cache_without_path_clears_every_project_and_exits(monkeypatch, tmp_path, fake_router, capsys):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "main.go").write_text("package main")
    scoped = AnalysisCache(project_path=project)
    scoped.save_endpoints(project, "go", [])
    models = AnalysisCache().cache_dir / "models"
    models.mkdir(parents=True, exist_ok=True)
    (models / "abc_x.json").write_text("[]")

    code = _run_main(monkeypatch, "--clear-cache", "--verbose")

    assert code == 0
    assert not scoped.endpoints_cache.exists()
    assert not (models / "abc_x.json").exists()
    assert "Cache cleared (1 model entries)" in capsys.readouterr().out
    fake_router.analyze_project.assert_not_called()


def test_main_clear_cache_with_path_continues_the_run(monkeypatch, tmp_path, fake_router, capsys):
    code = _run_main(monkeypatch, str(tmp_path), "--clear-cache")

    assert code == 0
    fake_router.analyze_project.assert_called_once()
