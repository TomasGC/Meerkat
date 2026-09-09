"""Unit tests for common/dedup.py — mechanical/AI finding reconciliation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.dedup import _NO_FINDINGS_TEXT, drop_near_duplicates, format_known_findings


def _violation(file: str = "app.py", line: int = 10, message: str = "issue") -> dict:
    return {"file": file, "line": line, "message": message}


class TestFormatKnownFindings:
    def test_empty_returns_placeholder(self):
        assert format_known_findings([]) == _NO_FINDINGS_TEXT

    def test_single_finding_rendered(self):
        result = format_known_findings([_violation(line=7, message="Hardcoded secret")])
        assert result == "- line 7: Hardcoded secret"

    def test_multiple_findings_one_per_line(self):
        result = format_known_findings([
            _violation(line=3, message="first"),
            _violation(line=9, message="second"),
        ])
        assert result.splitlines() == ["- line 3: first", "- line 9: second"]

    def test_findings_sorted_by_line(self):
        result = format_known_findings([
            _violation(line=42, message="late"),
            _violation(line=1, message="early"),
        ])
        assert result.splitlines() == ["- line 1: early", "- line 42: late"]

    def test_missing_keys_do_not_raise(self):
        assert format_known_findings([{}]) == "- line 0: "


class TestDropNearDuplicates:
    def test_exact_line_match_dropped(self):
        ai = [_violation(line=10, message="AI finding")]
        mechanical = [_violation(line=10, message="mechanical finding")]
        assert drop_near_duplicates(ai, mechanical) == []

    def test_within_proximity_dropped(self):
        ai = [_violation(line=12, message="AI finding")]
        mechanical = [_violation(line=10, message="mechanical finding")]
        assert drop_near_duplicates(ai, mechanical) == []

    def test_outside_proximity_kept(self):
        ai = [_violation(line=20, message="AI finding")]
        mechanical = [_violation(line=10, message="mechanical finding")]
        assert drop_near_duplicates(ai, mechanical) == ai

    def test_different_file_kept(self):
        ai = [_violation(file="other.py", line=10, message="AI finding")]
        mechanical = [_violation(file="app.py", line=10, message="mechanical finding")]
        assert drop_near_duplicates(ai, mechanical) == ai

    def test_custom_proximity_respected(self):
        ai = [_violation(line=20, message="AI finding")]
        mechanical = [_violation(line=10, message="mechanical finding")]
        assert drop_near_duplicates(ai, mechanical, proximity=10) == []

    def test_no_mechanical_keeps_everything(self):
        ai = [_violation(line=1), _violation(line=99)]
        assert drop_near_duplicates(ai, []) == ai

    def test_only_matching_entries_dropped(self):
        ai = [_violation(line=10, message="dup"), _violation(line=50, message="unique")]
        mechanical = [_violation(line=11, message="mechanical finding")]
        kept = drop_near_duplicates(ai, mechanical)
        assert [v["message"] for v in kept] == ["unique"]
