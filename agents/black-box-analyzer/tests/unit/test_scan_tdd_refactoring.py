#!/usr/bin/env python3
"""Tests for scan_tdd_refactoring.py"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scan_tdd_refactoring import _merge_blocker_runs

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
