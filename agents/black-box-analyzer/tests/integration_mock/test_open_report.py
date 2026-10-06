#!/usr/bin/env python3
"""Tests for open_report.py — int_mock tests (shutil.which patched)"""

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from open_report import main as open_report_main
from open_report import (
    step_collect,
    step_merge,
    step_open_browser,
    step_reportgenerator,
)


def test_step_merge_fallback_concatenates(temp_dir, minimal_lcov_file):
    output = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = step_merge([minimal_lcov_file], output)
    assert ok is True
    assert output.exists()
    assert "SF:" in output.read_text()


def test_step_merge_output_contains_all_sources(temp_dir):
    a = temp_dir / "a.lcov"
    b = temp_dir / "b.lcov"
    a.write_text("SF:src/a.py\nDA:1,1\nend_of_record\n")
    b.write_text("SF:src/b.py\nDA:2,1\nend_of_record\n")
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        step_merge([a, b], out)
    content = out.read_text()
    assert "src/a.py" in content
    assert "src/b.py" in content


def test_step_merge_skips_nonexistent_files(temp_dir, minimal_lcov_file):
    ghost = temp_dir / "ghost.lcov"
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value=None):
        ok = step_merge([minimal_lcov_file, ghost], out)
    assert ok is True


def test_step_reportgenerator_not_found_returns_false(temp_dir):
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            ok = step_reportgenerator("*.lcov", temp_dir / "report", "test")
    assert ok is False


def test_step_reportgenerator_warns_when_missing(temp_dir, capsys):
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            step_reportgenerator("*.lcov", temp_dir / "report", "test")
    captured = capsys.readouterr()
    assert "ReportGenerator not found" in captured.err


def test_step_reportgenerator_success_returns_true(temp_dir):
    with patch("shutil.which", return_value="/usr/bin/reportgenerator"), patch("open_report._run", return_value=0):
        ok = step_reportgenerator("*.lcov", temp_dir / "report", "test")
    assert ok is True


# ── step_collect ─────────────────────────────────────────────────────────────


def test_step_collect_returns_only_generated_tier_files(temp_dir):
    out = temp_dir / "tiers"
    out.mkdir()
    (out / "coverage_unit.lcov").write_text("SF:a\nend_of_record\n")
    with patch("open_report._run", return_value=0) as run:
        files = step_collect(temp_dir, out, ("unit", "e2e"))
    assert files == [out / "coverage_unit.lcov"]
    cmd = run.call_args.args[0]
    assert cmd[cmd.index("--tiers") + 1 : cmd.index("--output-dir")] == ["unit", "e2e"]


def test_step_collect_warns_and_continues_when_collector_fails(temp_dir, capsys):
    with patch("open_report._run", return_value=2):
        files = step_collect(temp_dir, temp_dir, ("unit",))
    assert files == []
    assert "Coverage collection had errors" in capsys.readouterr().err


# ── step_merge with the lcov tool ───────────────────────────────────────────


def test_step_merge_uses_lcov_tool_when_available(temp_dir, minimal_lcov_file):
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value="/usr/bin/lcov"), patch("open_report._run", return_value=0) as run:
        ok = step_merge([minimal_lcov_file], out)
    assert ok is True
    cmd = run.call_args.args[0]
    assert cmd[:3] == ["lcov", "--add-tracefile", str(minimal_lcov_file)]
    assert not out.exists()  # the (mocked) tool owns the output


def test_step_merge_falls_back_to_concatenation_when_lcov_fails(temp_dir, minimal_lcov_file, capsys):
    out = temp_dir / "combined.lcov"
    with patch("shutil.which", return_value="/usr/bin/lcov"), patch("open_report._run", return_value=1):
        ok = step_merge([minimal_lcov_file], out)
    assert ok is True
    assert "SF:src/main.py" in out.read_text(encoding="utf-8")
    assert "falling back to concatenation" in capsys.readouterr().err


# ── step_reportgenerator via the dotnet global tool ─────────────────────────


def test_step_reportgenerator_finds_dotnet_global_tool(temp_dir):
    def which(name):
        return "/usr/bin/dotnet" if name == "dotnet" else None

    listing = SimpleNamespace(stdout="dotnet-reportgenerator-globaltool  5.2.0  reportgenerator\n")
    report = temp_dir / "report"
    with (
        patch("shutil.which", side_effect=which),
        patch("subprocess.run", return_value=listing),
        patch("open_report._run", return_value=0) as run,
    ):
        ok = step_reportgenerator("a.lcov", report, "Demo")
    assert ok is True
    assert report.is_dir()
    cmd = run.call_args.args[0]
    assert cmd[0] == "reportgenerator"
    assert "-reports:a.lcov" in cmd
    assert "-title:Demo Coverage" in cmd


def test_step_reportgenerator_failure_returns_false(temp_dir):
    with patch("shutil.which", return_value="/usr/bin/reportgenerator"), patch("open_report._run", return_value=1):
        assert step_reportgenerator("*.lcov", temp_dir / "report", "x") is False


# ── step_open_browser ────────────────────────────────────────────────────────


@pytest.mark.parametrize(("system", "opener"), [("Darwin", "open"), ("Linux", "xdg-open")])
def test_step_open_browser_uses_platform_opener(temp_dir, system, opener):
    index = temp_dir / "index.html"
    index.write_text("<html></html>")
    with patch("platform.system", return_value=system), patch("subprocess.run") as run:
        step_open_browser(index)
    assert run.call_args.args[0] == [opener, index.resolve().as_uri()]


def test_step_open_browser_on_windows_uses_startfile(temp_dir, monkeypatch):
    index = temp_dir / "index.html"
    index.write_text("<html></html>")
    opened = []
    monkeypatch.setattr(os, "startfile", opened.append, raising=False)
    with patch("platform.system", return_value="Windows"):
        step_open_browser(index)
    assert opened == [str(index.resolve())]


# ── main (CLI) ───────────────────────────────────────────────────────────────


def _project_with_lcov(temp_dir, tiers=("unit",)):
    project = (temp_dir / "proj").resolve()  # main() resolves the path; Windows temp dirs may be 8.3 short names
    out = project / ".coverage-tiers"
    out.mkdir(parents=True)
    for tier in tiers:
        (out / f"coverage_{tier}.lcov").write_text(f"SF:src/{tier}.py\nDA:1,1\nend_of_record\n")
    return project, out


def _fake_reportgenerator(write_index=True):
    """A step_reportgenerator stand-in that writes what the real tool would."""

    def fake(lcov_glob, report_dir, project_name):
        report_dir.mkdir(parents=True, exist_ok=True)
        if write_index:
            (report_dir / "index.html").write_text("<html></html>")
        summary = {"summary": {"linecoverage": 91.0, "branchcoverage": 80.0, "assemblies": []}}
        (report_dir / "Summary.json").write_text(json.dumps(summary))
        fake.calls.append((lcov_glob, report_dir, project_name))
        return True

    fake.calls = []
    return fake


def test_main_skip_collect_without_lcov_files_returns_one(temp_dir, monkeypatch, capsys):
    project = temp_dir / "proj"
    project.mkdir()
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project), "--skip-collect"])
    assert open_report_main() == 1
    assert "No lcov files found" in capsys.readouterr().err


def test_main_collect_producing_nothing_returns_one(temp_dir, monkeypatch, capsys):
    project = temp_dir / "proj"
    project.mkdir()
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project)])
    with patch("open_report.step_collect", return_value=[]):
        assert open_report_main() == 1
    assert "No lcov files generated" in capsys.readouterr().err


def test_main_full_pipeline_merges_reports_and_skips_browser(temp_dir, monkeypatch, capsys):
    project, out = _project_with_lcov(temp_dir, ("unit", "e2e"))
    fake = _fake_reportgenerator()
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project), "--skip-collect", "--no-browser"])
    with (
        patch("shutil.which", return_value=None),
        patch("open_report.step_reportgenerator", side_effect=fake),
        patch("open_report.step_open_browser") as browser,
    ):
        assert open_report_main() == 0
    combined = out / "combined.lcov"
    assert "src/unit.py" in combined.read_text(encoding="utf-8")
    assert "src/e2e.py" in combined.read_text(encoding="utf-8")
    lcov_glob, report_dir, name = fake.calls[0]
    assert lcov_glob == str(combined)
    assert report_dir == project.resolve() / "coverage-report"
    assert name == "proj"
    browser.assert_not_called()
    err = capsys.readouterr().err
    assert "Line coverage   : 91.0%" in err
    assert "Report:" in err


def test_main_opens_browser_by_default(temp_dir, monkeypatch):
    project, _ = _project_with_lcov(temp_dir)
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project), "--skip-collect"])
    with (
        patch("shutil.which", return_value=None),
        patch("open_report.step_reportgenerator", side_effect=_fake_reportgenerator()),
        patch("open_report.step_open_browser") as browser,
    ):
        assert open_report_main() == 0
    assert browser.call_args.args[0].name == "index.html"


def test_main_skip_merge_passes_glob_to_reportgenerator(temp_dir, monkeypatch):
    project, out = _project_with_lcov(temp_dir)
    fake = _fake_reportgenerator()
    monkeypatch.setattr(
        sys,
        "argv",
        ["open_report.py", str(project), "--skip-collect", "--skip-merge", "--no-browser", "--project-name", "Demo"],
    )
    with patch("open_report.step_reportgenerator", side_effect=fake):
        assert open_report_main() == 0
    assert fake.calls[0][0] == str(out / "*.lcov")
    assert fake.calls[0][2] == "Demo"
    assert not (out / "combined.lcov").exists()


def test_main_reportgenerator_failure_points_to_raw_files(temp_dir, monkeypatch, capsys):
    project, out = _project_with_lcov(temp_dir)
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project), "--skip-collect"])
    with patch("shutil.which", return_value=None), patch("open_report.step_reportgenerator", return_value=False):
        assert open_report_main() == 1
    err = capsys.readouterr().err
    assert f"Raw lcov files available in: {out}" in err
    assert "Combined lcov:" in err


def test_main_missing_index_html_returns_one(temp_dir, monkeypatch, capsys):
    project, _ = _project_with_lcov(temp_dir)
    monkeypatch.setattr(sys, "argv", ["open_report.py", str(project), "--skip-collect", "--no-browser"])
    with (
        patch("shutil.which", return_value=None),
        patch("open_report.step_reportgenerator", side_effect=_fake_reportgenerator(write_index=False)),
    ):
        assert open_report_main() == 1
    assert "index.html not found" in capsys.readouterr().err
