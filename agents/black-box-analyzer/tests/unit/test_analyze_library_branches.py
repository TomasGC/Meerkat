#!/usr/bin/env python3
"""Tests for analyze_library_branches.py — unit tests (_merge_runs)"""

from pathlib import Path

from analyze_library_branches import _merge_runs

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
