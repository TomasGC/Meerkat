#!/usr/bin/env python3
"""The one finding schema shared by the engine's checkers and orchestrator.

Wire name for the category field stays ``principle`` — CCA calls it a
principle, SSA a checker, BBA a test gap, and renaming would churn every
checker and every test assertion for a cosmetic gain. Revisit in a later
sub-issue if it still bothers us.
"""

from typing import TypedDict


class Finding(TypedDict, total=False):
    principle: str
    file: str
    line: int
    severity: str
    message: str
    suggestion: str


class CheckerResult(TypedDict, total=False):
    principle: str
    success: bool
    violations: list[Finding]
    files_analyzed: int
    duration_ms: int
    error: str
    cache_hits: int
    cache_total: int
