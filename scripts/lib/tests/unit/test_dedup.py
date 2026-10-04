#!/usr/bin/env python3
"""Tests for lib/engine/dedup.py — whole-file (line 0) findings in reconciliation (#20)."""

from lib.engine.dedup import drop_near_duplicates, format_known_findings


def _v(line: int, file: str = "a.py") -> dict:
    return {"file": file, "line": line, "message": f"at {line}"}


class TestWholeFileFindings:
    def test_whole_file_finding_does_not_hide_findings_on_early_lines(self):
        """ "No unit test for this file" and "function on line 2 needs a test" are not the same defect."""
        kept = drop_near_duplicates([_v(1), _v(2), _v(3)], [_v(0)])
        assert [v["line"] for v in kept] == [1, 2, 3]

    def test_whole_file_findings_still_match_each_other(self):
        assert drop_near_duplicates([_v(0)], [_v(0)]) == []

    def test_ai_whole_file_finding_is_not_hidden_by_a_line_finding(self):
        assert drop_near_duplicates([_v(0)], [_v(2)]) == [_v(0)]

    def test_line_findings_keep_the_proximity_rule(self):
        kept = drop_near_duplicates([_v(10), _v(13), _v(14)], [_v(10)])
        assert [v["line"] for v in kept] == [14]

    def test_other_files_are_never_matched(self):
        assert drop_near_duplicates([_v(0, "b.py")], [_v(0, "a.py")]) == [_v(0, "b.py")]


class TestFormatKnownFindings:
    def test_whole_file_finding_is_rendered_as_such(self):
        text = format_known_findings([{"line": 0, "message": "No unit test file found"}])
        assert text == "- whole file: No unit test file found"

    def test_line_findings_keep_their_line(self):
        text = format_known_findings([{"line": 7, "message": "MD5"}, {"line": 0, "message": "untested"}])
        assert text.splitlines() == ["- whole file: untested", "- line 7: MD5"]
