#!/usr/bin/env python3
"""Tests for lib/engine/orchestrator.py — one run per language group, merged per checker."""

import json
import sys
import types
from pathlib import Path

import pytest

from lib.engine import discovery, orchestrator


@pytest.fixture(autouse=True)
def fresh_discovery_cache():
    discovery._DISCOVERY_CACHE.clear()
    yield
    discovery._DISCOVERY_CACHE.clear()


@pytest.fixture
def fake_checkers(monkeypatch):
    """Install checker modules that record every (language, files) they are run with."""
    calls: list[tuple[str, str, list[str]]] = []

    def install(name: str, kinds: tuple[str, ...] | None = None) -> str:
        module = types.ModuleType(f"fake_checkers.{name}")

        def run(path, language, files=None):
            calls.append((name, language, sorted(f.name for f in files)))
            return {
                "principle": name.upper(),
                "success": True,
                "files_analyzed": len(files),
                "duration_ms": 1,
                "violations": [
                    {
                        "principle": name.upper(),
                        "file": f.name,
                        "line": 1,
                        "severity": "low",
                        "message": f"{language} file",
                        "suggestion": "",
                    }
                    for f in files
                ],
            }

        module.run = run
        if kinds is not None:
            module.FILE_KINDS = kinds
        monkeypatch.setitem(sys.modules, module.__name__, module)
        return module.__name__

    install.calls = calls
    return install


def _project(root: Path) -> Path:
    for name in ("app.py", "util.py", "main.go", "ci.yaml", "Dockerfile", "notes.txt"):
        (root / name).write_text("x\n", encoding="utf-8")
    return root


def _main(root: Path, registry: dict[str, str], tmp_path: Path) -> dict:
    out = tmp_path / "report.json"
    orchestrator.main(
        registry=registry,
        app_name="Test",
        label_singular="checker",
        cache_dir=tmp_path / "cache",
        max_workers=2,
        argv=["--path", str(root), "--full", "--no-stream", "--output", str(out)],
    )
    return json.loads(out.read_text(encoding="utf-8"))


class TestRunByLanguage:
    def test_default_checker_runs_once_per_code_language(self, tmp_path, fake_checkers):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        registry = {"plain": fake_checkers("plain")}
        _main(root, registry, tmp_path)
        assert fake_checkers.calls == [("plain", "python", ["app.py", "util.py"]), ("plain", "go", ["main.go"])]

    def test_file_kinds_add_config_and_data_languages(self, tmp_path, fake_checkers):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        registry = {"infra": fake_checkers("infra", ("code", "data", "config"))}
        _main(root, registry, tmp_path)
        languages = [language for _, language, _ in fake_checkers.calls]
        assert languages == ["python", "go", "yaml", "dockerfile"]

    def test_no_run_ever_sees_mixed(self, tmp_path, fake_checkers):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        (root / "cmd.go").write_text("x\n", encoding="utf-8")  # 2 py / 2 go: the label is mixed
        report = _main(root, {"infra": fake_checkers("infra", ("code", "data", "config"))}, tmp_path)
        assert report["language"] == "mixed"
        assert "mixed" not in {language for _, language, _ in fake_checkers.calls}

    def test_report_lists_languages_analyzed(self, tmp_path, fake_checkers):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        report = _main(
            root, {"plain": fake_checkers("plain"), "infra": fake_checkers("infra", ("code", "data"))}, tmp_path
        )
        assert report["languages"] == {"python": 2, "go": 1, "yaml": 1}

    def test_results_merge_into_one_entry_per_checker(self, tmp_path, fake_checkers):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        report = _main(root, {"plain": fake_checkers("plain")}, tmp_path)
        assert report["summary"] == {"PLAIN": {"count": 3, "high": 0, "medium": 0, "low": 3}}
        assert report["files_analyzed"] == 3

    def test_incremental_list_is_grouped_too(self, tmp_path, fake_checkers, monkeypatch):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        monkeypatch.setattr(orchestrator, "get_staged_files", lambda path: [root / "main.go", root / "ci.yaml"])
        out = tmp_path / "report.json"
        orchestrator.main(
            registry={"plain": fake_checkers("plain")},
            app_name="Test",
            label_singular="checker",
            cache_dir=tmp_path / "c",
            argv=["--path", str(root), "--staged", "--no-stream", "--output", str(out)],
        )
        assert fake_checkers.calls == [("plain", "go", ["main.go"])]

    def test_unimportable_checker_still_reports_its_error(self, tmp_path):
        root = tmp_path / "p"
        root.mkdir()
        _project(root)
        report = _main(root, {"broken": "fake_checkers.does_not_exist"}, tmp_path)
        assert report["summary"] == {"broken": {"count": 0, "high": 0, "medium": 0, "low": 0}}


class TestMergeRuns:
    def test_counters_add_up(self):
        merged = orchestrator._merge_runs(
            "x",
            [
                {
                    "principle": "X",
                    "success": True,
                    "violations": [{"a": 1}],
                    "files_analyzed": 2,
                    "duration_ms": 5,
                    "cache_hits": 1,
                    "cache_total": 2,
                },
                {
                    "principle": "X",
                    "success": True,
                    "violations": [{"b": 2}],
                    "files_analyzed": 3,
                    "duration_ms": 7,
                    "cache_hits": 0,
                    "cache_total": 3,
                },
            ],
        )
        assert merged == {
            "principle": "X",
            "success": True,
            "violations": [{"a": 1}, {"b": 2}],
            "files_analyzed": 5,
            "duration_ms": 12,
            "cache_hits": 1,
            "cache_total": 5,
        }

    def test_one_failed_run_fails_the_checker_and_keeps_its_error(self):
        merged = orchestrator._merge_runs(
            "x",
            [
                {"principle": "X", "success": True, "violations": [], "files_analyzed": 1, "duration_ms": 1},
                {
                    "principle": "x",
                    "success": False,
                    "error": "boom",
                    "violations": [],
                    "files_analyzed": 0,
                    "duration_ms": 0,
                },
            ],
        )
        assert merged["success"] is False
        assert merged["error"] == "boom"

    def test_no_runs_is_an_empty_success(self):
        merged = orchestrator._merge_runs("x", [])
        assert merged == {"principle": "x", "success": True, "violations": [], "files_analyzed": 0, "duration_ms": 0}

    def test_no_cache_counters_when_no_run_had_them(self):
        merged = orchestrator._merge_runs(
            "x", [{"principle": "X", "success": True, "violations": [], "files_analyzed": 1, "duration_ms": 1}]
        )
        assert "cache_hits" not in merged and "cache_total" not in merged
