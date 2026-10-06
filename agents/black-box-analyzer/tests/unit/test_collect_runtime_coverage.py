#!/usr/bin/env python3
"""Tests for collect_runtime_coverage.py — unit tests"""

import json
from pathlib import Path

from collect_runtime_coverage import (
    TIER_MARKERS,
    _convert_go_cover_to_lcov,
)


def test_tier_markers_pytest_values_are_lists():
    for tier, markers in TIER_MARKERS.items():
        val = markers["pytest"]
        assert isinstance(val, list), f"TIER_MARKERS['{tier}']['pytest'] must be list, got {type(val)}"


def test_tier_markers_all_tiers_present():
    for tier in ("unit", "int_mock", "int_real", "e2e"):
        assert tier in TIER_MARKERS
        assert "pytest" in TIER_MARKERS[tier]
        assert "jest" in TIER_MARKERS[tier]


def test_convert_go_cover_to_lcov_basic(minimal_go_cover_file, temp_dir):
    out = temp_dir / "out.lcov"
    _convert_go_cover_to_lcov(minimal_go_cover_file, out)
    assert out.exists()
    content = out.read_text()
    assert "SF:" in content
    assert "DA:" in content
    assert "end_of_record" in content


def test_convert_go_cover_to_lcov_correct_line_numbers(minimal_go_cover_file, temp_dir):
    out = temp_dir / "out.lcov"
    _convert_go_cover_to_lcov(minimal_go_cover_file, out)
    content = out.read_text()
    assert "DA:10,3" in content
    assert "DA:15,0" in content


def test_convert_go_cover_to_lcov_empty_input(temp_dir):
    cov = temp_dir / "empty.out"
    cov.write_text("mode: atomic\n")
    out = temp_dir / "out.lcov"
    _convert_go_cover_to_lcov(cov, out)
    assert out.exists()
    content = out.read_text()
    assert "SF:" not in content


def test_convert_go_cover_to_lcov_multiple_files(temp_dir):
    cov = temp_dir / "multi.out"
    cov.write_text("mode: atomic\n" "pkg/a.go:1.1,2.1 1 5\n" "pkg/b.go:3.1,4.1 1 2\n")
    out = temp_dir / "out.lcov"
    _convert_go_cover_to_lcov(cov, out)
    content = out.read_text()
    assert content.count("SF:") == 2
    assert content.count("end_of_record") == 2


def test_collect_coverage_unknown_language_no_exception(temp_dir):
    from collect_runtime_coverage import collect_coverage

    unknown_dir = temp_dir / "unknown-proj"
    unknown_dir.mkdir()
    (unknown_dir / "README.txt").write_text("nothing special\n")
    outputs = collect_coverage(unknown_dir, temp_dir / "cov", ("unit",), dry_run=True)
    assert isinstance(outputs, dict)


# ── main ──────────────────────────────────────────────────────────────────────


def test_main_dry_run_prints_manifest_and_writes_output(sample_python_project, temp_dir, monkeypatch, capsys):
    import collect_runtime_coverage

    manifest_file = temp_dir / "manifest.json"
    cov_dir = temp_dir / "cov"
    monkeypatch.setattr(collect_runtime_coverage, "_which", lambda name: True)
    monkeypatch.setattr(
        "sys.argv",
        [
            "collect_runtime_coverage.py",
            str(sample_python_project),
            "--tiers",
            "unit",
            "e2e",
            "--output-dir",
            str(cov_dir),
            "--dry-run",
            "--output",
            str(manifest_file),
        ],
    )
    rc = collect_runtime_coverage.main()
    expected = {"unit": str(cov_dir / "coverage_unit.lcov"), "e2e": str(cov_dir / "coverage_e2e.lcov")}
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert json.loads(manifest_file.read_text()) == expected


def test_main_defaults_output_dir_inside_project(sample_python_project, monkeypatch, capsys):
    import collect_runtime_coverage

    monkeypatch.setattr(collect_runtime_coverage, "_which", lambda name: True)
    monkeypatch.setattr("sys.argv", ["collect_runtime_coverage.py", str(sample_python_project), "--dry-run"])
    assert collect_runtime_coverage.main() == 0
    manifest = json.loads(capsys.readouterr().out)
    assert set(manifest) == {"unit", "int_mock", "int_real", "e2e"}
    assert all(Path(p).parent == sample_python_project.resolve() / ".coverage-tiers" for p in manifest.values())


def test_main_returns_one_when_nothing_generated(temp_dir, monkeypatch, capsys):
    import collect_runtime_coverage

    empty = temp_dir / "empty"
    empty.mkdir()
    monkeypatch.setattr("sys.argv", ["collect_runtime_coverage.py", str(empty), "--dry-run"])
    assert collect_runtime_coverage.main() == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {}
    assert "No coverage files generated" in captured.err
