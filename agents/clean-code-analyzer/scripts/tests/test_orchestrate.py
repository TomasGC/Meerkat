"""Tests for orchestrate.py — deduplication, severity filtering, summary building."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrate import _build_summary, _SEVERITY_ORDER


class TestBuildSummary:
    def test_counts_by_severity(self):
        results = [
            {
                "principle": "SOLID",
                "violations": [
                    {"severity": "high"},
                    {"severity": "medium"},
                    {"severity": "low"},
                    {"severity": "high"},
                ],
            }
        ]
        summary = _build_summary(results)
        assert summary["SOLID"]["count"] == 4
        assert summary["SOLID"]["high"] == 2
        assert summary["SOLID"]["medium"] == 1
        assert summary["SOLID"]["low"] == 1

    def test_empty_violations(self):
        results = [{"principle": "DRY", "violations": []}]
        summary = _build_summary(results)
        assert summary["DRY"]["count"] == 0

    def test_multiple_principles(self):
        results = [
            {"principle": "SOLID", "violations": [{"severity": "high"}]},
            {"principle": "DRY", "violations": [{"severity": "low"}, {"severity": "low"}]},
        ]
        summary = _build_summary(results)
        assert summary["SOLID"]["count"] == 1
        assert summary["DRY"]["count"] == 2


class TestDeduplication:
    """Test the deduplication logic inline (same logic as orchestrate.main)."""

    def _dedup(self, all_results):
        violations = []
        seen = set()
        for result in all_results:
            for v in result.get("violations", []):
                key = (v.get("file"), v.get("line"), v.get("principle"))
                if key not in seen:
                    seen.add(key)
                    violations.append(v)
        return violations

    def test_removes_duplicates(self):
        v = {"file": "a.py", "line": 10, "principle": "SOLID", "severity": "high"}
        results = [
            {"violations": [v]},
            {"violations": [v]},
        ]
        deduped = self._dedup(results)
        assert len(deduped) == 1

    def test_keeps_different_lines(self):
        v1 = {"file": "a.py", "line": 10, "principle": "SOLID"}
        v2 = {"file": "a.py", "line": 20, "principle": "SOLID"}
        results = [{"violations": [v1, v2]}]
        deduped = self._dedup(results)
        assert len(deduped) == 2

    def test_keeps_different_principles(self):
        v1 = {"file": "a.py", "line": 10, "principle": "SOLID"}
        v2 = {"file": "a.py", "line": 10, "principle": "DRY"}
        results = [{"violations": [v1, v2]}]
        deduped = self._dedup(results)
        assert len(deduped) == 2


class TestSeverityFiltering:
    def test_severity_order(self):
        assert _SEVERITY_ORDER["high"] < _SEVERITY_ORDER["medium"]
        assert _SEVERITY_ORDER["medium"] < _SEVERITY_ORDER["low"]

    def test_high_only_filter(self):
        violations = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        min_sev = _SEVERITY_ORDER["high"]
        filtered = [v for v in violations if _SEVERITY_ORDER.get(v["severity"], 2) <= min_sev]
        assert len(filtered) == 1
        assert filtered[0]["severity"] == "high"

    def test_low_filter_keeps_all(self):
        violations = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        min_sev = _SEVERITY_ORDER["low"]
        filtered = [v for v in violations if _SEVERITY_ORDER.get(v["severity"], 2) <= min_sev]
        assert len(filtered) == 3
