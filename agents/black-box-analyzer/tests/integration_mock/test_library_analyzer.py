#!/usr/bin/env python3
"""Tests for library_analyzer.py — int_mock tests (analyze() with patched _run_script)"""

import json
from unittest.mock import MagicMock, patch

from bba.models import ProjectType
from library_analyzer import LibraryAnalyzer


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

    branch_payload = {"methods": [{"method": "Foo.Do", "signature": "()", "source_file": "", "branches": []}]}

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

    for script, args in captured_args:
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

    for script, args in captured_args:
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


_BRANCHES = {
    "methods": [
        {
            "method": "Parser.parse",
            "signature": "parse(text)",
            "source_file": "src/parser.py",
            "branches": [
                {"condition": "valid text", "outcome": "returns tree", "test_scenario": "parse valid text"},
                {"condition": "empty text", "outcome": "raises ValueError", "test_scenario": "reject empty text"},
            ],
        }
    ]
}


def _fake_scripts(captured):
    def fake_run_script(script, *args):
        captured.append((script, args))
        return _BRANCHES if "branches" in script else {"blockers": []}

    return fake_run_script


def test_analyze_builds_entry_points_scenarios_and_risks(temp_dir):
    (temp_dir / "src").mkdir()
    project_info = MagicMock()
    project_info.language.value = "python"
    captured = []

    with patch("library_analyzer._run_script", side_effect=_fake_scripts(captured)):
        result = LibraryAnalyzer().analyze(temp_dir, project_info)

    assert [ep.name for ep in result.entry_points] == ["Parser.parse"]
    assert result.entry_points[0].metadata == {"signature": "parse(text)"}
    assert [s.scenario_type for s in result.scenarios] == ["happy_path", "error"]
    assert len(result.risk_assessment) == 2
    assert result.coverage_matrix.total_scenarios == 2
    assert result.coverage_matrix.tested_scenarios == 0
    assert result.metadata["branch_count"] == 2
    # src/ is preferred over the project root as the analysis target
    assert result.metadata["src_path"] == str(temp_dir / "src")
    assert all(args[0] == str(temp_dir / "src") for _script, args in captured)


def test_analyze_unknown_language_asks_scripts_to_autodetect(temp_dir):
    project_info = MagicMock()
    project_info.language.value = "unknown"
    captured = []

    with patch("library_analyzer._run_script", side_effect=_fake_scripts(captured)):
        result = LibraryAnalyzer().analyze(temp_dir, project_info)

    assert result.metadata["language"] == "auto"
    assert all(args[args.index("--language") + 1] == "auto" for _script, args in captured)


def test_analyze_typed_agents_flags_reach_branch_script_only(temp_dir):
    project_info = MagicMock()
    project_info.language.value = "python"
    captured = []

    with patch("library_analyzer._run_script", side_effect=_fake_scripts(captured)):
        LibraryAnalyzer().analyze(temp_dir, project_info, typed_agents=True, include_e2e=True)

    args_by_script = dict(captured)
    assert "--typed-agents" in args_by_script["analyze_library_branches.py"]
    assert "--e2e" in args_by_script["analyze_library_branches.py"]
    assert "--typed-agents" not in args_by_script["scan_tdd_refactoring.py"]


def test_analyze_marks_scenarios_covered_by_previous_test_run(temp_dir):
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()
    (claude_dir / "bbanalysis-last-tests.json").write_text(
        json.dumps(
            {
                "tests": [
                    {"name": "test reject empty text", "file_path": "t.py", "line_number": 4, "framework": "pytest"},
                    {"name": "test_other", "framework": "no-such-framework"},
                ]
            }
        )
    )
    project_info = MagicMock()
    project_info.language.value = "python"

    with patch("library_analyzer._run_script", side_effect=_fake_scripts([])):
        result = LibraryAnalyzer().analyze(temp_dir, project_info)

    assert [t.name for t in result.test_cases] == ["test reject empty text", "test_other"]
    assert result.test_cases[1].framework.value == "unknown"
    assert result.coverage_matrix.tested_scenarios == 1
    assert result.coverage_matrix.coverage_percent == 50.0


def test_analyze_ignores_corrupt_previous_test_run(temp_dir):
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir()
    (claude_dir / "bbanalysis-last-tests.json").write_text("{not json")
    project_info = MagicMock()
    project_info.language.value = "python"

    with patch("library_analyzer._run_script", side_effect=_fake_scripts([])):
        result = LibraryAnalyzer().analyze(temp_dir, project_info)

    assert result.test_cases == []
    assert result.coverage_matrix.tested_scenarios == 0
