#!/usr/bin/env python3
"""Reconcile mechanical and AI findings — prompt hints plus proximity deduplication."""

_NO_FINDINGS_TEXT = "None found mechanically. Report everything you detect."
_PROXIMITY_LINES = 3


def format_known_findings(violations: list[dict]) -> str:
    """Render mechanical violations as a prompt block so the AI does not repeat them."""
    if not violations:
        return _NO_FINDINGS_TEXT
    ordered = sorted(violations, key=lambda v: v.get("line", 0))
    return "\n".join(f"- {_where(v.get('line', 0))}: {v.get('message', '')}" for v in ordered)


def _where(line: int) -> str:
    """Line 0 is a whole-file finding (e.g. "no test file"), not a finding on line zero."""
    return f"line {line}" if line else "whole file"


def _near(ai_line: int, mechanical_line: int, proximity: int) -> bool:
    """Whole-file findings only match each other: one never hides a per-line finding below it."""
    if not mechanical_line or not ai_line:
        return ai_line == mechanical_line
    return abs(ai_line - mechanical_line) <= proximity


def drop_near_duplicates(
    ai_violations: list[dict],
    mechanical_violations: list[dict],
    proximity: int = _PROXIMITY_LINES,
) -> list[dict]:
    """Drop AI violations within `proximity` lines of a mechanical one in the same file.

    The prompt already lists mechanical findings, but models do not always comply.
    """
    known: dict[str, list[int]] = {}
    for violation in mechanical_violations:
        known.setdefault(violation.get("file", ""), []).append(violation.get("line", 0))

    kept = []
    for violation in ai_violations:
        lines = known.get(violation.get("file", ""), [])
        if any(_near(violation.get("line", 0), line, proximity) for line in lines):
            continue
        kept.append(violation)
    return kept
