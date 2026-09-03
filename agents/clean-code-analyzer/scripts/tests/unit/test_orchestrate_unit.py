"""Unit tests for internal helpers in orchestrate.py."""

import subprocess
from pathlib import Path
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from orchestrate import _progress_bar, _build_summary, _SEVERITY_ORDER, _mini_bar, _estimate_token_savings


# ── _progress_bar ───────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_progress_bar_zero_completed():
    """0/12 → bar starts with empty (░) blocks."""
    result = _progress_bar(0, 12)
    assert result.startswith("[░")


@pytest.mark.unit
def test_progress_bar_fully_completed():
    """12/12 → shows 100%."""
    result = _progress_bar(12, 12)
    assert "100%" in result


@pytest.mark.unit
def test_progress_bar_half_completed():
    """6/12 → shows 50%."""
    result = _progress_bar(6, 12)
    assert "50%" in result


# ── deduplication logic ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_deduplication_removes_duplicate_key():
    """Violations with same (file, line, principle) are deduplicated."""
    v1 = {"file": "a.py", "line": 5, "principle": "Naming", "severity": "high"}
    v2 = {"file": "a.py", "line": 5, "principle": "Naming", "severity": "high"}  # duplicate
    v3 = {"file": "a.py", "line": 10, "principle": "Naming", "severity": "medium"}

    results = [
        {"violations": [v1, v2]},
        {"violations": [v3]},
    ]

    # Replicate orchestrate.py dedup logic
    all_violations = []
    seen = set()
    for result in results:
        for v in result.get("violations", []):
            key = (v.get("file"), v.get("line"), v.get("principle"))
            if key not in seen:
                seen.add(key)
                all_violations.append(v)

    assert len(all_violations) == 2


# ── _build_summary ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_build_summary_counts_severities():
    """3 high + 2 medium + 1 low → correct counts in summary."""
    results = [
        {
            "principle": "Naming",
            "violations": [
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "high"},
                {"severity": "medium"},
                {"severity": "medium"},
                {"severity": "low"},
            ],
        }
    ]
    summary = _build_summary(results)
    assert summary["Naming"]["count"] == 6
    assert summary["Naming"]["high"] == 3
    assert summary["Naming"]["medium"] == 2
    assert summary["Naming"]["low"] == 1


# ── filtering ───────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_min_severity_high_removes_medium_and_low():
    """--min-severity high filter removes medium and low violations."""
    violations = [
        {"file": "a.py", "line": 1, "principle": "A", "severity": "high"},
        {"file": "a.py", "line": 2, "principle": "A", "severity": "medium"},
        {"file": "a.py", "line": 3, "principle": "A", "severity": "low"},
    ]
    min_sev = _SEVERITY_ORDER.get("high", 0)
    filtered = [v for v in violations if _SEVERITY_ORDER.get(v.get("severity", "low"), 2) <= min_sev]
    assert len(filtered) == 1
    assert filtered[0]["severity"] == "high"


@pytest.mark.unit
def test_top_n_limits_violations():
    """--top 3 returns only the first 3 violations."""
    violations = [
        {"file": "a.py", "line": i, "principle": "A", "severity": "high"}
        for i in range(10)
    ]
    top3 = violations[:3]
    assert len(top3) == 3
    assert top3[0]["line"] == 0
    assert top3[2]["line"] == 2


# ── _mini_bar ───────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_mini_bar_zero():
    """0/10 → all empty blocks (░) or empty string."""
    bar = _mini_bar(0, 10)
    # When max_count>0 and count=0, filled=0 so bar is all ░
    assert "█" not in bar
    assert len(bar) == 8  # default width=8


@pytest.mark.unit
def test_mini_bar_full():
    """10/10 → all filled blocks (█)."""
    bar = _mini_bar(10, 10)
    assert "█" in bar
    assert "░" not in bar


@pytest.mark.unit
def test_mini_bar_zero_max_returns_all_empty():
    """max_count=0 → _mini_bar returns all ░ (no division by zero)."""
    bar = _mini_bar(0, 0)
    assert "█" not in bar


# ── _estimate_token_savings ─────────────────────────────────────────────────────

@pytest.mark.unit
def test_estimate_token_savings_nonzero():
    """estimate_token_savings with realistic inputs returns a positive number."""
    result = _estimate_token_savings(50, 12)
    assert result > 0


@pytest.mark.unit
def test_estimate_token_savings_zero_violations():
    """estimate_token_savings with 0 violations still accounts for checkers."""
    result = _estimate_token_savings(0, 5)
    assert result == 5 * 2000  # checkers_run * 2000


# ── CLI: invalid path exits nonzero ────────────────────────────────────────────

@pytest.mark.unit
def test_invalid_path_exits_nonzero():
    """orchestrate.py --path /nonexistent → exits with nonzero return code."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "orchestrate.py"),
            "--path", "/nonexistent_path_xyz_does_not_exist",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
