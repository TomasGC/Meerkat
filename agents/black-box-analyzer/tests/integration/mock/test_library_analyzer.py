#!/usr/bin/env python3
"""Tests for library_analyzer.py — int_mock tests (analyze() with patched _run_script)"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from library_analyzer import LibraryAnalyzer
from common.models import ProjectType

def test_analyze_graceful_when_script_fails(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    with patch("library_analyzer._run_script", return_value=None):
        result = analyzer.analyze(temp_dir, project_info)

    assert result.project_type == ProjectType.LIBRARY
    assert result.entry_points == []
    assert result.scenarios == []

def test_analyze_tdd_blockers_populated_from_refactoring_data(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    branch_payload = {"methods": []}
    refactor_payload = {"blockers": [{"location": "Foo.Bar", "anti_pattern": "new_in_method"}]}

    def fake_run_script(script, *args):
        if "analyze_library_branches" in script:
            return branch_payload
        if "scan_tdd_refactoring" in script:
            return refactor_payload
        return None

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        result = analyzer.analyze(temp_dir, project_info)

    assert result.metadata["tdd_blockers"] == refactor_payload["blockers"]
    assert result.metadata["tdd_blocker_count"] == 1

def test_analyze_phase1_fails_phase4b_succeeds(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    refactor_payload = {"blockers": [{"location": "X.Y", "anti_pattern": "hardcoded_io"}]}

    def fake_run_script(script, *args):
        if "analyze_library_branches" in script:
            return None
        return refactor_payload

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        result = analyzer.analyze(temp_dir, project_info)

    assert result.entry_points == []
    assert result.metadata["tdd_blocker_count"] == 1

def test_analyze_phase4b_fails_phase1_succeeds(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    branch_payload = {
        "methods": [{"method": "Foo.Do", "signature": "()", "source_file": "", "branches": []}]
    }

    def fake_run_script(script, *args):
        if "analyze_library_branches" in script:
            return branch_payload
        return None

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        result = analyzer.analyze(temp_dir, project_info)

    assert len(result.entry_points) == 1
    assert result.metadata["tdd_blockers"] == []
    assert result.metadata["tdd_blocker_count"] == 0

def test_analyze_refactoring_data_missing_blockers_key(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    def fake_run_script(script, *args):
        if "analyze_library_branches" in script:
            return {"methods": []}
        return {"summary": "no blockers key here"}

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        result = analyzer.analyze(temp_dir, project_info)

    assert result.metadata["tdd_blockers"] == []
    assert result.metadata["tdd_blocker_count"] == 0

def test_analyze_tdd_blocker_count_matches_len(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    blockers = [
        {"location": "A.B", "anti_pattern": "new_in_method"},
        {"location": "C.D", "anti_pattern": "no_interface"},
        {"location": "E.F", "anti_pattern": "hardcoded_io"},
    ]

    def fake_run_script(script, *args):
        if "analyze_library_branches" in script:
            return {"methods": []}
        return {"blockers": blockers}

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        result = analyzer.analyze(temp_dir, project_info)

    assert result.metadata["tdd_blocker_count"] == len(result.metadata["tdd_blockers"])
    assert result.metadata["tdd_blocker_count"] == 3

def test_analyze_passes_agents_flag_when_agents_gt_1(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    captured_args = []

    def fake_run_script(script, *args):
        captured_args.append((script, args))
        return {"methods": []} if "branches" in script else {"blockers": []}

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        analyzer.analyze(temp_dir, project_info, agents=2)

    for (script, args) in captured_args:
        assert "--agents" in args, f"--agents not in args for {script}: {args}"
        idx = args.index("--agents")
        assert args[idx + 1] == "2"

def test_analyze_no_agents_flag_when_agents_eq_1(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    captured_args = []

    def fake_run_script(script, *args):
        captured_args.append((script, args))
        return {"methods": []} if "branches" in script else {"blockers": []}

    with patch("library_analyzer._run_script", side_effect=fake_run_script):
        analyzer.analyze(temp_dir, project_info, agents=1)

    for (script, args) in captured_args:
        assert "--agents" not in args

def test_analyze_graceful_both_fail_has_empty_tdd_blockers(temp_dir):
    analyzer = LibraryAnalyzer()
    project_info = MagicMock()
    project_info.language.value = "python"

    with patch("library_analyzer._run_script", return_value=None):
        result = analyzer.analyze(temp_dir, project_info)

    assert "tdd_blockers" in result.metadata
    assert result.metadata["tdd_blockers"] == []
    assert result.metadata["tdd_blocker_count"] == 0
