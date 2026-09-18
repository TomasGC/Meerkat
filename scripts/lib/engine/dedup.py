#!/usr/bin/env python3
"""Reconcile mechanical and AI findings — prompt hints plus proximity deduplication."""

_NO_FINDINGS_TEXT = "None found mechanically. Report everything you detect."
_PROXIMITY_LINES = 3


def format_known_findings(violations: list[dict]) -> str:
    """Render mechanical violations as a prompt block so the AI does not repeat them."""
    if not violations:
        return _NO_FINDINGS_TEXT
    ordered = sorted(violations, key=lambda v: v.get("line", 0))
    return "\n".join(f"- line {v.get('line', 0)}: {v.get('message', '')}" for v in ordered)


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
        if any(abs(violation.get("line", 0) - line) <= proximity for line in lines):
            continue
        kept.append(violation)
    return kept
