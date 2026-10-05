#!/usr/bin/env python3
"""Tests for scan_tdd_refactoring.py"""

import json
import sys
from unittest.mock import patch

import pytest
import scan_tdd_refactoring
from scan_tdd_refactoring import _merge_blocker_runs, get_source_files, summarize

# ── _merge_blocker_runs ───────────────────────────────────────────────────────


def test_merge_blocker_runs_empty_returns_empty():
    assert _merge_blocker_runs([]) == []


def test_merge_blocker_runs_single_empty_run():
    assert _merge_blocker_runs([[]]) == []


def test_merge_blocker_runs_deduplicates_identical_key():
    blocker = {"location": "Foo.Bar", "anti_pattern": "static_method_call"}
    run1 = [blocker]
    run2 = [{"location": "Foo.Bar", "anti_pattern": "static_method_call"}]
    result = _merge_blocker_runs([run1, run2])
    assert len(result) == 1


def test_merge_blocker_runs_same_location_different_pattern():
    b1 = {"location": "Foo.Bar", "anti_pattern": "static_method_call"}
    b2 = {"location": "Foo.Bar", "anti_pattern": "new_in_method"}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 2


def test_merge_blocker_runs_different_location_same_pattern():
    b1 = {"location": "Foo.Bar", "anti_pattern": "static_method_call"}
    b2 = {"location": "Baz.Qux", "anti_pattern": "static_method_call"}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 2


def test_merge_blocker_runs_anti_pattern_key_is_case_sensitive():
    b1 = {"location": "Foo.Bar", "anti_pattern": "static_method_call"}
    b2 = {"location": "Foo.Bar", "anti_pattern": "Static_Method_Call"}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 2


def test_merge_blocker_runs_location_key_is_case_insensitive():
    b1 = {"location": "Foo.Bar", "anti_pattern": "static_method_call"}
    b2 = {"location": "foo.bar", "anti_pattern": "static_method_call"}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 1


def test_merge_blocker_runs_location_truncated_to_80_for_key():
    base = "x" * 80
    b1 = {"location": base + "AAA", "anti_pattern": "new_in_method"}
    b2 = {"location": base + "ZZZ", "anti_pattern": "new_in_method"}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 1


def test_merge_blocker_runs_missing_location_key():
    blocker = {"anti_pattern": "new_in_method"}
    result = _merge_blocker_runs([[blocker]])
    assert len(result) == 1
    assert result[0] is blocker


def test_merge_blocker_runs_missing_anti_pattern_key():
    blocker = {"location": "Foo.Bar"}
    result = _merge_blocker_runs([[blocker]])
    assert len(result) == 1
    assert result[0] is blocker


def test_merge_blocker_runs_three_runs_correct_union():
    b1 = {"location": "A.method", "anti_pattern": "static_method_call"}
    b2 = {"location": "B.method", "anti_pattern": "new_in_method"}
    b3 = {"location": "C.method", "anti_pattern": "hardcoded_io"}
    result = _merge_blocker_runs([[b1], [b2], [b3]])
    assert len(result) == 3


def test_merge_blocker_runs_both_keys_missing():
    b1 = {}
    b2 = {}
    result = _merge_blocker_runs([[b1], [b2]])
    assert len(result) == 1


# ── get_source_files ──────────────────────────────────────────────────────────


def _library(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("class Service: pass")
    (tmp_path / "src" / "test_service.py").write_text("def test_x(): pass")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "helpers.py").write_text("x = 1")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "gen.py").write_text("x = 1")
    (tmp_path / "README.md").write_text("docs")
    return tmp_path


def test_get_source_files_skips_tests_and_build_output(tmp_path):
    root = _library(tmp_path)
    assert get_source_files(root, "python") == [root / "src" / "service.py"]


def test_get_source_files_unknown_language_finds_nothing(tmp_path):
    assert get_source_files(_library(tmp_path), "cobol") == []


# ── summarize ─────────────────────────────────────────────────────────────────


def test_summarize_counts_patterns_and_unlocked_tests():
    blockers = [
        {"anti_pattern": "new_in_method", "tests_unlocked": ["a", "b"]},
        {"anti_pattern": "new_in_method", "tests_unlocked": ["c"]},
        {"tests_unlocked": []},
    ]
    assert summarize(blockers) == {
        "total_blockers": 3,
        "total_tests_unlocked": 3,
        "by_anti_pattern": {"new_in_method": 2, "unknown": 1},
    }


# ── main ──────────────────────────────────────────────────────────────────────

_BLOCKERS = [
    {
        "location": "A.x",
        "anti_pattern": "hardcoded_io",
        "effort": "Large",
        "tests_unlocked": ["t1"],
        "source_file_name": "b.py",
    },
    {
        "location": "B.y",
        "anti_pattern": "new_in_method",
        "effort": "Tiny",
        "tests_unlocked": ["t1", "t2", "t3"],
        "source_file_name": "a.py",
    },
]


def _main(monkeypatch, *argv, server=True, blockers=_BLOCKERS):
    monkeypatch.setattr(sys, "argv", ["scan_tdd_refactoring.py", *argv])
    with patch.object(scan_tdd_refactoring, "check_server_available", return_value=server), patch.object(
        scan_tdd_refactoring, "analyze_file_with_model", side_effect=lambda *a, **k: [dict(b) for b in blockers]
    ) as model:
        code = scan_tdd_refactoring.main()
    return code, model


def test_main_missing_path_exits_one(monkeypatch, tmp_path, capsys):
    code, model = _main(monkeypatch, str(tmp_path / "nope"))
    assert code == 1
    assert "does not exist" in capsys.readouterr().err
    model.assert_not_called()


def test_main_server_unavailable_exits_one(monkeypatch, tmp_path, capsys):
    code, _ = _main(monkeypatch, str(tmp_path), server=False)
    assert code == 1
    assert "not available" in capsys.readouterr().err


def test_main_no_source_files_exits_one(monkeypatch, tmp_path, capsys):
    code, _ = _main(monkeypatch, str(tmp_path), "--language", "python")
    assert code == 1
    assert "No python source files found" in capsys.readouterr().err


def test_main_prints_report_sorted_by_tests_unlocked(monkeypatch, tmp_path, capsys):
    root = _library(tmp_path)
    code, model = _main(monkeypatch, str(root), "--language", "python", "--max-chars", "100")

    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["language"] == "python"
    assert [b["location"] for b in report["blockers"]] == ["B.y", "A.x"]
    assert report["summary"]["total_tests_unlocked"] == 4
    assert model.call_args.kwargs["max_chars"] == 100


@pytest.mark.parametrize("sort_by, expected", [("effort", ["B.y", "A.x"]), ("file", ["B.y", "A.x"])])
def test_main_sort_options(monkeypatch, tmp_path, capsys, sort_by, expected):
    # The model returns A.x first; both orders must put B.y (Tiny effort, a.py) first
    _main(monkeypatch, str(_library(tmp_path)), "--language", "python", "--sort-by", sort_by)
    assert [b["location"] for b in json.loads(capsys.readouterr().out)["blockers"]] == expected


def test_main_auto_detects_language_and_writes_output(monkeypatch, tmp_path, capsys):
    root = _library(tmp_path)
    out = tmp_path / "out.json"
    code, _ = _main(monkeypatch, str(root), "--output", str(out), "--verbose")

    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["language"] == "python"
    err = capsys.readouterr().err
    assert "Auto-detected language: python" in err
    assert "Written to" in err


def test_main_multiple_agents_merge_duplicate_blockers(monkeypatch, tmp_path, capsys):
    code, model = _main(monkeypatch, str(_library(tmp_path)), "--language", "python", "--agents", "3", "--verbose")

    assert code == 0
    assert model.call_count == 3
    out = capsys.readouterr()
    assert json.loads(out.out)["summary"]["total_blockers"] == 2
    assert "Merged 3 runs: 2 unique blockers" in out.err
