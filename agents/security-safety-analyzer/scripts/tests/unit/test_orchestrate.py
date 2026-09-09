"""Unit tests for internal helpers in orchestrate.py."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrate import (
    CHECKERS,
    _build_summary,
    _detect_base_branch,
    _estimate_token_savings,
    _mini_bar,
    _progress_bar,
    _run_checker,
)


class TestProgressBar:
    def test_zero_completed(self):
        result = _progress_bar(0, 5)
        assert result.startswith("[░")

    def test_fully_completed(self):
        result = _progress_bar(5, 5)
        assert "100%" in result

    def test_half_completed(self):
        result = _progress_bar(2, 4)
        assert "50%" in result

    def test_zero_total_no_crash(self):
        result = _progress_bar(0, 0)
        assert "0%" in result


class TestMiniBar:
    def test_zero_max_all_empty(self):
        assert _mini_bar(3, 0) == "░" * 8

    def test_full_bar(self):
        result = _mini_bar(10, 10)
        assert "█" in result


class TestBuildSummary:
    def test_counts_severities(self):
        results = [
            {"principle": "Security", "violations": [
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "medium"},
            ]},
            {"principle": "CrashBug", "violations": [
                {"severity": "low"},
            ]},
        ]
        summary = _build_summary(results)
        assert summary["Security"]["count"] == 3
        assert summary["Security"]["high"] == 2
        assert summary["Security"]["medium"] == 1
        assert summary["CrashBug"]["low"] == 1

    def test_empty_results(self):
        summary = _build_summary([])
        assert summary == {}

    def test_no_violations_checker(self):
        results = [{"principle": "Concurrency", "violations": []}]
        summary = _build_summary(results)
        assert summary["Concurrency"]["count"] == 0


class TestCheckersDict:
    def test_all_checkers_present(self):
        expected = {
            "security", "crypto", "deserialization", "misconfiguration", "sensitive_data",
            "crash_bugs", "concurrency", "resource_leaks", "error_handling", "prompt_injection",
        }
        assert set(CHECKERS.keys()) == expected

    def test_every_checker_module_is_importable(self):
        import importlib
        for key, module_path in CHECKERS.items():
            mod = importlib.import_module(module_path)
            assert callable(mod.run), f"{key}: run() missing"

    def test_all_module_paths_start_with_checkers(self):
        for key, module_path in CHECKERS.items():
            assert module_path.startswith("checkers."), f"{key}: {module_path}"


class TestDeduplication:
    def test_duplicate_key_removed(self):
        v1 = {"file": "a.py", "line": 5, "principle": "Security", "severity": "high"}
        v2 = {"file": "a.py", "line": 5, "principle": "Security", "severity": "high"}
        v3 = {"file": "a.py", "line": 10, "principle": "Security", "severity": "low"}
        results = [{"violations": [v1, v2]}, {"violations": [v3]}]

        all_violations = []
        seen = set()
        for result in results:
            for v in result.get("violations", []):
                key = (v.get("file"), v.get("line"), v.get("principle"))
                if key not in seen:
                    seen.add(key)
                    all_violations.append(v)

        assert len(all_violations) == 2


class TestRunChecker:
    def test_import_error_returns_error_dict(self, tmp_path):
        result = _run_checker("fake", "checkers.nonexistent_xyz", tmp_path, "python")
        assert result["success"] is False
        assert "error" in result
        assert result["violations"] == []

    def test_estimate_token_savings(self):
        savings = _estimate_token_savings(total_violations=10, checkers_run=5)
        assert savings > 0


class TestDetectBaseBranch:
    def test_returns_none_for_non_git_dir(self, tmp_path):
        result = _detect_base_branch(tmp_path)
        assert result is None
