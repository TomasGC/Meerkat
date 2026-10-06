#!/usr/bin/env python3
"""Tests for diff_analysis.py — unit tests"""

import json

import pytest

from diff_analysis import (
    compare_analyses,
    format_markdown,
    format_summary,
    load_analysis,
)


def _make_analysis(
    coverage: float, untested: int, critical: int = 0, high: int = 0, by_endpoint: dict | None = None
) -> dict:
    return {
        "coverage_summary": {
            "coverage_percent": coverage,
            "untested_scenarios": untested,
            "by_endpoint": by_endpoint or {},
        },
        "risk_summary": {
            "by_level": {"CRITICAL": critical, "HIGH": high},
        },
    }


def test_load_analysis_valid(temp_dir):
    data = {"coverage_summary": {"coverage_percent": 42.0}}
    f = temp_dir / "analysis.json"
    f.write_text(json.dumps(data))
    result = load_analysis(f)
    assert result["coverage_summary"]["coverage_percent"] == 42.0


def test_load_analysis_missing_file(temp_dir):
    with pytest.raises(FileNotFoundError):
        load_analysis(temp_dir / "nonexistent.json")


def test_load_analysis_invalid_json(temp_dir):
    f = temp_dir / "bad.json"
    f.write_text("not json {{{")
    with pytest.raises(ValueError):
        load_analysis(f)


def test_compare_coverage_improved():
    baseline = _make_analysis(50.0, 10)
    current = _make_analysis(75.0, 5)
    diff = compare_analyses(baseline, current)
    assert diff.coverage_delta == pytest.approx(25.0)
    assert diff.new_coverage == 75.0
    assert diff.resolved_gaps == 5
    assert diff.new_gaps == 0


def test_compare_coverage_regressed():
    baseline = _make_analysis(80.0, 3)
    current = _make_analysis(60.0, 8)
    diff = compare_analyses(baseline, current)
    assert diff.coverage_delta == pytest.approx(-20.0)
    assert diff.resolved_gaps == 0
    assert diff.new_gaps == 5


def test_compare_critical_risk_change():
    baseline = _make_analysis(50.0, 5, critical=1, high=2)
    current = _make_analysis(60.0, 3, critical=3, high=1)
    diff = compare_analyses(baseline, current)
    assert diff.old_critical == 1
    assert diff.new_critical == 3
    assert diff.old_high == 2
    assert diff.new_high == 1


def test_compare_endpoint_improved():
    baseline = _make_analysis(50.0, 5, by_endpoint={"/users": {"coverage_percent": 40.0}})
    current = _make_analysis(70.0, 2, by_endpoint={"/users": {"coverage_percent": 90.0}})
    diff = compare_analyses(baseline, current)
    assert len(diff.improved_endpoints) == 1
    assert diff.improved_endpoints[0]["endpoint"] == "/users"
    assert diff.improved_endpoints[0]["delta"] == pytest.approx(50.0)


def test_compare_endpoint_regressed():
    baseline = _make_analysis(70.0, 2, by_endpoint={"/orders": {"coverage_percent": 80.0}})
    current = _make_analysis(50.0, 5, by_endpoint={"/orders": {"coverage_percent": 30.0}})
    diff = compare_analyses(baseline, current)
    assert len(diff.regressed_endpoints) == 1
    assert diff.regressed_endpoints[0]["delta"] == pytest.approx(-50.0)


def test_compare_new_and_removed_endpoints():
    baseline = _make_analysis(50.0, 5, by_endpoint={"/old": {"coverage_percent": 50.0}})
    current = _make_analysis(50.0, 5, by_endpoint={"/new": {"coverage_percent": 50.0}})
    diff = compare_analyses(baseline, current)
    assert "/new" in diff.new_endpoints
    assert "/old" in diff.removed_endpoints


def test_compare_empty_analyses():
    diff = compare_analyses({}, {})
    assert diff.coverage_delta == 0.0
    assert diff.resolved_gaps == 0
    assert diff.new_gaps == 0


def test_compare_uses_by_entry_point_fallback():
    baseline = {
        "coverage_summary": {
            "coverage_percent": 40.0,
            "untested_scenarios": 5,
            "by_entry_point": {"/ep": {"coverage_percent": 20.0}},
        },
        "risk_summary": {"by_level": {}},
    }
    current = {
        "coverage_summary": {
            "coverage_percent": 80.0,
            "untested_scenarios": 1,
            "by_entry_point": {"/ep": {"coverage_percent": 90.0}},
        },
        "risk_summary": {"by_level": {}},
    }
    diff = compare_analyses(baseline, current)
    assert len(diff.improved_endpoints) == 1


def test_to_dict_trend_improved():
    diff = compare_analyses(_make_analysis(40.0, 5), _make_analysis(60.0, 3))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "improved"


def test_to_dict_trend_regressed():
    diff = compare_analyses(_make_analysis(60.0, 3), _make_analysis(40.0, 7))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "regressed"


def test_to_dict_trend_unchanged():
    diff = compare_analyses(_make_analysis(50.0, 5), _make_analysis(50.0, 5))
    d = diff.to_dict()
    assert d["coverage"]["trend"] == "unchanged"


def test_format_markdown_has_headers():
    diff = compare_analyses(_make_analysis(40.0, 5), _make_analysis(60.0, 3))
    md = format_markdown(diff)
    assert "# Analysis Comparison Report" in md
    assert "Coverage Summary" in md
    assert "Gap Summary" in md


def test_format_summary_shows_regression():
    baseline = _make_analysis(80.0, 2, by_endpoint={"/x": {"coverage_percent": 80.0}})
    current = _make_analysis(60.0, 5, by_endpoint={"/x": {"coverage_percent": 20.0}})
    diff = compare_analyses(baseline, current)
    summary = format_summary(diff)
    assert "Regressions" in summary or "egressed" in summary


# ── format_markdown sections ──────────────────────────────────────────────────


def _endpoints(n: int, coverage: float) -> dict:
    return {f"/ep{i}": {"coverage_percent": coverage} for i in range(n)}


def test_format_markdown_net_regression_line():
    md = format_markdown(compare_analyses(_make_analysis(60.0, 2), _make_analysis(50.0, 5)))
    assert "**Net regression**: 3 more gaps" in md


def test_format_markdown_net_change_stable():
    md = format_markdown(compare_analyses(_make_analysis(50.0, 4), _make_analysis(50.0, 4)))
    assert "**Net change**: 0 (stable)" in md


def test_format_markdown_improved_and_regressed_tables():
    baseline = _make_analysis(
        50.0, 5, by_endpoint={"/up": {"coverage_percent": 20.0}, "/down": {"coverage_percent": 90.0}}
    )
    current = _make_analysis(
        50.0, 5, by_endpoint={"/up": {"coverage_percent": 70.0}, "/down": {"coverage_percent": 40.0}}
    )
    md = format_markdown(compare_analyses(baseline, current))
    assert "## 📈 Improved Endpoints" in md
    assert "| /up | 20.0% | 70.0% | +50.0% |" in md
    assert "## 📉 Regressed Endpoints" in md
    assert "| /down | 90.0% | 40.0% | -50.0% |" in md


def test_format_markdown_lists_new_and_removed_endpoints_truncated_at_20():
    baseline = _make_analysis(50.0, 5, by_endpoint={f"/old{i}": {"coverage_percent": 1.0} for i in range(22)})
    current = _make_analysis(50.0, 5, by_endpoint=_endpoints(25, 1.0))
    md = format_markdown(compare_analyses(baseline, current))
    assert "## ➕ New Endpoints" in md
    assert "- /ep19" in md
    assert "- /ep20" not in md
    assert "- ... and 5 more" in md
    assert "## ➖ Removed Endpoints" in md
    assert "- ... and 2 more" in md


def test_format_markdown_critical_increase_uses_alarm_marker():
    md = format_markdown(compare_analyses(_make_analysis(50.0, 5, critical=0), _make_analysis(50.0, 5, critical=2)))
    assert "🚨 **CRITICAL**: 0 → 2 (+2)" in md


# ── format_summary lines ──────────────────────────────────────────────────────


def test_format_summary_reports_new_gaps_and_new_critical():
    summary = format_summary(compare_analyses(_make_analysis(50.0, 1), _make_analysis(40.0, 4, critical=2)))
    assert "❌ New gaps: 3" in summary
    assert "🚨 NEW CRITICAL: +2 gaps" in summary


def test_format_summary_reports_resolved_critical():
    summary = format_summary(compare_analyses(_make_analysis(40.0, 4, critical=3), _make_analysis(50.0, 1)))
    assert "✅ Resolved: 3 gaps" in summary
    assert "✅ Resolved CRITICAL: 3 gaps" in summary


def test_format_summary_lists_at_most_three_regressions():
    baseline = _make_analysis(50.0, 5, by_endpoint=_endpoints(5, 90.0))
    current = _make_analysis(50.0, 5, by_endpoint=_endpoints(5, 10.0))
    summary = format_summary(compare_analyses(baseline, current))
    assert "⚠️ Regressions: 5 endpoints" in summary
    assert summary.count("(90.0% → 10.0%)") == 3


# ── main ──────────────────────────────────────────────────────────────────────


def _write_pair(temp_dir, baseline: dict, current: dict):
    b = temp_dir / "baseline.json"
    c = temp_dir / "current.json"
    b.write_text(json.dumps(baseline))
    c.write_text(json.dumps(current))
    return b, c


def _run_main(monkeypatch, *argv):
    import diff_analysis

    monkeypatch.setattr("sys.argv", ["diff_analysis.py", *map(str, argv)])
    return diff_analysis.main()


def test_main_summary_to_stdout_exits_zero_without_regression(temp_dir, monkeypatch, capsys):
    b, c = _write_pair(temp_dir, _make_analysis(40.0, 5), _make_analysis(60.0, 3))
    assert _run_main(monkeypatch, b, c) == 0
    assert "Coverage: 40.00% → 60.00% (+20.00%)" in capsys.readouterr().out


def test_main_json_format_written_to_file(temp_dir, monkeypatch, capsys):
    b, c = _write_pair(temp_dir, _make_analysis(40.0, 5), _make_analysis(60.0, 3))
    out = temp_dir / "diff.json"
    assert _run_main(monkeypatch, b, c, "--format", "json", "--output", out) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["gaps"]["resolved"] == 2
    assert "Diff report written to" in capsys.readouterr().err


def test_main_markdown_format(temp_dir, monkeypatch, capsys):
    b, c = _write_pair(temp_dir, _make_analysis(40.0, 5), _make_analysis(60.0, 3))
    assert _run_main(monkeypatch, b, c, "-f", "markdown") == 0
    assert capsys.readouterr().out.startswith("# Analysis Comparison Report")


def test_main_new_critical_exits_one(temp_dir, monkeypatch):
    b, c = _write_pair(temp_dir, _make_analysis(50.0, 5), _make_analysis(60.0, 3, critical=1))
    assert _run_main(monkeypatch, b, c) == 1


def test_main_regressed_endpoint_exits_one(temp_dir, monkeypatch):
    b, c = _write_pair(
        temp_dir,
        _make_analysis(50.0, 5, by_endpoint={"/x": {"coverage_percent": 80.0}}),
        _make_analysis(50.0, 5, by_endpoint={"/x": {"coverage_percent": 10.0}}),
    )
    assert _run_main(monkeypatch, b, c) == 1


def test_main_missing_file_reports_error(temp_dir, monkeypatch, capsys):
    assert _run_main(monkeypatch, temp_dir / "none.json", temp_dir / "none2.json") == 1
    assert "Error: Analysis file not found" in capsys.readouterr().err
