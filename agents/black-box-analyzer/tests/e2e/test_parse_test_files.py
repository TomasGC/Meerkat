#!/usr/bin/env python3
"""Tests for parse_test_files.py — e2e tests (subprocess.run on script)"""

import json
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


def test_cli_go_project_json_output(sample_go_project):
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "parse_test_files.py"),
         str(sample_go_project), "--language", "go"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["test_count"] == 3
