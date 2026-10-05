#!/usr/bin/env python3
"""Tests for lib/engine/hybrid.py — the `ai_filter` narrowing of the AI pass (#20)."""

from pathlib import Path
from unittest.mock import patch

from lib.engine.hybrid import run_hybrid


def _mechanical(found: list[str]):
    def mechanical(path: Path, files: list | None) -> tuple[list[dict], int]:
        return [
            {"principle": "P", "file": f, "line": 0, "severity": "medium", "message": "untested", "suggestion": ""}
            for f in found
        ], len(files or [])

    return mechanical


def test_ai_pass_only_sees_accepted_files(tmp_path):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text("x = 1\n")
    b.write_text("y = 2\n")
    with patch("lib.engine.hybrid.check_server_available", return_value=True), patch(
        "lib.engine.hybrid.analyze_files_parallel", return_value=[]
    ) as ai:
        run_hybrid(
            tmp_path,
            "python",
            "P",
            "some_prompt",
            {},
            files=[a, b],
            mechanical_fn=_mechanical(["a.py"]),
            ai_filter=lambda f: f == a,
        )
    assert ai.call_args.args[0] == [a]


def test_nothing_accepted_means_no_ai_call(tmp_path):
    a = tmp_path / "a.py"
    a.write_text("x = 1\n")
    with patch("lib.engine.hybrid.check_server_available", return_value=True), patch(
        "lib.engine.hybrid.analyze_files_parallel"
    ) as ai:
        result = run_hybrid(
            tmp_path,
            "python",
            "P",
            "some_prompt",
            {},
            files=[a],
            mechanical_fn=_mechanical([]),
            ai_filter=lambda f: False,
        )
    ai.assert_not_called()
    assert result["files_analyzed"] == 1


def test_without_filter_every_file_reaches_the_ai(tmp_path):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text("x = 1\n")
    b.write_text("y = 2\n")
    with patch("lib.engine.hybrid.check_server_available", return_value=True), patch(
        "lib.engine.hybrid.analyze_files_parallel", return_value=[]
    ) as ai:
        run_hybrid(tmp_path, "python", "P", "some_prompt", {}, files=[a, b], mechanical_fn=_mechanical([]))
    assert ai.call_args.args[0] == [a, b]
