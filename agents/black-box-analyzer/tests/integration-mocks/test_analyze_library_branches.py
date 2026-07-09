#!/usr/bin/env python3
"""Tests for analyze_library_branches.py — int_mock tests (--agents CLI path)"""

import sys
from pathlib import Path
from unittest.mock import patch

from analyze_library_branches import main

def test_main_agents_1_does_not_use_executor(tmp_path, monkeypatch):
    (tmp_path / "dummy.py").write_text("def foo(): pass")
    monkeypatch.setattr(sys, "argv", [
        "analyze_library_branches.py",
        str(tmp_path),
        "--language", "python",
        "--agents", "1",
    ])
    with patch("analyze_library_branches.check_ollama_available", return_value=True), \
         patch("analyze_library_branches.analyze_library", return_value=[]), \
         patch("concurrent.futures.ThreadPoolExecutor") as mock_executor, \
         patch("builtins.print"):
        main()
    mock_executor.assert_not_called()

def test_main_agents_2_calls_merge_runs(tmp_path, monkeypatch):
    (tmp_path / "dummy.py").write_text("def foo(): pass")
    monkeypatch.setattr(sys, "argv", [
        "analyze_library_branches.py",
        str(tmp_path),
        "--language", "python",
        "--agents", "2",
    ])
    with patch("analyze_library_branches.check_ollama_available", return_value=True), \
         patch("analyze_library_branches.analyze_library", return_value=[]) as mock_analyze, \
         patch("builtins.print"):
        main()
    assert mock_analyze.call_count == 2
