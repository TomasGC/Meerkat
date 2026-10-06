#!/usr/bin/env python3
"""Tests for analyze_library_branches.py — unit tests (local AI mocked at analyze_file_with_model)"""

import json
import sys
from unittest.mock import patch

import analyze_library_branches as alb
from analyze_library_branches import _merge_runs, analyze_file_typed, analyze_library, get_source_files


def test_merge_runs_empty_runs_returns_empty():
    assert _merge_runs([]) == []


def test_merge_runs_single_empty_run_returns_empty():
    assert _merge_runs([[]]) == []


def test_merge_runs_single_run_method_no_branches():
    result = _merge_runs([[{"method": "Foo", "branches": []}]])
    assert len(result) == 1
    assert result[0]["method"] == "Foo"
    assert result[0]["branches"] == []


def test_merge_runs_deduplicates_identical_method_condition():
    branch = {"condition": "valid input", "outcome": "returns result"}
    run1 = [{"method": "Foo", "branches": [branch]}]
    run2 = [{"method": "Foo", "branches": [branch]}]
    result = _merge_runs([run1, run2])
    assert len(result) == 1
    assert len(result[0]["branches"]) == 1


def test_merge_runs_merges_unique_conditions_same_method():
    run1 = [{"method": "Foo", "branches": [{"condition": "cond A"}]}]
    run2 = [{"method": "Foo", "branches": [{"condition": "cond B"}]}]
    result = _merge_runs([run1, run2])
    assert len(result) == 1
    conditions = {b["condition"] for b in result[0]["branches"]}
    assert conditions == {"cond A", "cond B"}


def test_merge_runs_keeps_all_methods():
    run1 = [{"method": "Foo", "branches": [{"condition": "x"}]}]
    run2 = [{"method": "Bar", "branches": [{"condition": "y"}]}]
    result = _merge_runs([run1, run2])
    method_names = {m["method"] for m in result}
    assert method_names == {"Foo", "Bar"}


def test_merge_runs_condition_dedup_case_insensitive():
    run1 = [{"method": "Foo", "branches": [{"condition": "NULL input"}]}]
    run2 = [{"method": "Foo", "branches": [{"condition": "null input"}]}]
    result = _merge_runs([run1, run2])
    assert len(result[0]["branches"]) == 1


def test_merge_runs_condition_truncated_to_80_for_key():
    base = "x" * 80
    run1 = [{"method": "Foo", "branches": [{"condition": base + "AAAA"}]}]
    run2 = [{"method": "Foo", "branches": [{"condition": base + "BBBB"}]}]
    result = _merge_runs([run1, run2])
    assert len(result[0]["branches"]) == 1


def test_merge_runs_method_missing_key_falls_back_to_empty_string():
    run = [{"signature": "def something()", "branches": [{"condition": "x"}]}]
    result = _merge_runs([run])
    assert len(result) == 1
    assert result[0].get("method", "") == ""


def test_merge_runs_branch_missing_condition_key():
    run = [{"method": "Foo", "branches": [{"outcome": "returns result"}]}]
    result = _merge_runs([run])
    assert len(result) == 1
    assert len(result[0]["branches"]) == 1


def test_merge_runs_first_run_metadata_wins():
    run1 = [{"method": "Foo", "signature": "sig1", "branches": []}]
    run2 = [{"method": "Foo", "signature": "sig2", "branches": []}]
    result = _merge_runs([run1, run2])
    assert result[0]["signature"] == "sig1"


def test_merge_runs_three_runs_union_of_unique_branches():
    run1 = [{"method": "Foo", "branches": [{"condition": "cond A"}]}]
    run2 = [{"method": "Foo", "branches": [{"condition": "cond B"}]}]
    run3 = [{"method": "Foo", "branches": [{"condition": "cond C"}]}]
    result = _merge_runs([run1, run2, run3])
    assert len(result) == 1
    assert len(result[0]["branches"]) == 3


def test_merge_runs_asymmetric_runs_one_empty():
    result = _merge_runs([[], [{"method": "Foo", "branches": [{"condition": "x"}]}]])
    assert len(result) == 1
    assert result[0]["method"] == "Foo"
    assert len(result[0]["branches"]) == 1


# ── get_source_files ──────────────────────────────────────────────────────────


def _library(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "core.py").write_text("def run(): pass")
    (tmp_path / "pkg" / "util.py").write_text("def helper(): pass")
    (tmp_path / "pkg" / "core_test.py").write_text("def test_run(): pass")
    (tmp_path / "spec").mkdir()
    (tmp_path / "spec" / "fixtures.py").write_text("x = 1")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.py").write_text("x = 1")
    return tmp_path


def test_get_source_files_returns_sorted_non_test_sources(tmp_path):
    root = _library(tmp_path)
    assert get_source_files(root, "python") == [root / "pkg" / "core.py", root / "pkg" / "util.py"]


# ── analyze_file_typed ────────────────────────────────────────────────────────


def _typed_model(_file, _language, _role, prompt_name, **_kwargs):
    """One method per typed prompt; 'shared' is returned by every agent."""
    return [
        {
            "method": "run",
            "signature": f"sig-{prompt_name}",
            "branches": [{"condition": "shared"}, {"condition": f"only {prompt_name}"}],
        }
    ]


def test_analyze_file_typed_tags_and_merges_per_test_type(tmp_path):
    with patch.object(alb, "analyze_file_with_model", side_effect=_typed_model) as model:
        methods = analyze_file_typed(tmp_path / "core.py", "python", "analyzer")

    assert {c.args[3] for c in model.call_args_list} == {
        "analyze_branches_unit",
        "analyze_branches_int_mock",
        "analyze_branches_int_real",
    }
    assert len(methods) == 1
    branches = methods[0]["branches"]
    # "shared" survives once per tier: the dedup key includes the test type hint
    assert sorted(b["test_type_hint"] for b in branches if b["condition"] == "shared") == [
        "INT_MOCK",
        "INT_REAL",
        "UNIT",
    ]
    assert len(branches) == 6


def test_analyze_file_typed_includes_e2e_on_request(tmp_path):
    with patch.object(alb, "analyze_file_with_model", side_effect=_typed_model) as model:
        methods = analyze_file_typed(tmp_path / "core.py", "python", "analyzer", include_e2e=True)

    assert model.call_count == 4
    assert "E2E" in {b["test_type_hint"] for b in methods[0]["branches"]}


# ── analyze_library ───────────────────────────────────────────────────────────


def test_analyze_library_no_sources_warns_and_returns_empty(tmp_path, capsys):
    assert analyze_library(tmp_path, "python", "analyzer", verbose=False) == []
    assert "No python source files found" in capsys.readouterr().err


def test_analyze_library_aggregates_every_file(tmp_path, capsys):
    root = _library(tmp_path)
    found = {"core.py": [{"method": "run"}], "util.py": []}
    with patch.object(alb, "analyze_file_with_model", side_effect=lambda f, *a, **k: found[f.name]):
        methods = analyze_library(root, "python", "analyzer", verbose=True)

    assert methods == [{"method": "run"}]
    err = capsys.readouterr().err
    assert "Source files: 2" in err
    assert "1 public method(s) found" in err


def test_analyze_library_typed_agents_route_through_typed_analysis(tmp_path, capsys):
    root = _library(tmp_path)
    with patch.object(alb, "analyze_file_typed", return_value=[{"method": "m"}]) as typed:
        methods = analyze_library(root, "python", "analyzer", verbose=True, typed_agents=True, include_e2e=True)

    assert methods == [{"method": "m"}, {"method": "m"}]
    assert typed.call_args.kwargs["include_e2e"] is True
    assert "Typed agents: ['unit', 'int_mock', 'int_real', 'e2e']" in capsys.readouterr().err


# ── main ──────────────────────────────────────────────────────────────────────


def _main(monkeypatch, *argv, server=True, methods=None):
    monkeypatch.setattr(sys, "argv", ["analyze_library_branches.py", *argv])
    payload = methods if methods is not None else [{"method": "run", "branches": [{"condition": "a"}]}]
    with patch.object(alb, "check_server_available", return_value=server), patch.object(
        alb, "analyze_file_with_model", side_effect=lambda *a, **k: [dict(m) for m in payload]
    ):
        return alb.main()


def test_main_missing_path_exits_one(monkeypatch, tmp_path, capsys):
    assert _main(monkeypatch, str(tmp_path / "missing")) == 1
    assert "does not exist" in capsys.readouterr().err


def test_main_server_unavailable_exits_one(monkeypatch, tmp_path, capsys):
    assert _main(monkeypatch, str(tmp_path), server=False) == 1
    assert "not available" in capsys.readouterr().err


def test_main_prints_method_and_branch_counts(monkeypatch, tmp_path, capsys):
    assert _main(monkeypatch, str(_library(tmp_path)), "--language", "python") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["method_count"] == 2
    assert report["branch_count"] == 2


def test_main_auto_language_writes_output_file(monkeypatch, tmp_path, capsys):
    root = _library(tmp_path)
    out = tmp_path / "methods.json"
    assert _main(monkeypatch, str(root), "--output", str(out), "--verbose") == 0

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["language"] == "python"
    err = capsys.readouterr().err
    assert "Auto-detected language: python" in err
    assert "Total: 2 methods, 2 branches" in err


def test_main_agents_merge_identical_runs(monkeypatch, tmp_path, capsys):
    assert _main(monkeypatch, str(_library(tmp_path)), "--language", "python", "--agents", "2", "--verbose") == 0
    out = capsys.readouterr()
    # Both files report the same method name, so the runs collapse to one method
    assert json.loads(out.out)["method_count"] == 1
    assert "Merged 2 runs: 1 unique methods" in out.err
