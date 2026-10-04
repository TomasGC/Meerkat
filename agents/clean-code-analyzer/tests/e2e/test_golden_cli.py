"""Golden fixture projects through the real CLI — mechanical checkers only, no AI involved."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.testing import golden  # noqa: E402

_ORCHESTRATE = Path(__file__).resolve().parents[2] / "scripts" / "orchestrate.py"
_CHECKS = "dry,naming,comments,lod,inheritance"
_PRINCIPLES = {"DRY", "Naming", "Comments", "LawOfDemeter", "CompositionOverInheritance"}


@pytest.mark.parametrize("project", golden.project_names())
def test_mechanical_output_matches_expected(project, tmp_path):
    root = golden.project_path(project)
    result = subprocess.run(
        [sys.executable, str(_ORCHESTRATE), "--path", str(root),
         "--checks", _CHECKS, "--full", "--format", "json", "--no-stream"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "CCA_CACHE_DIR": str(tmp_path / "cache")},
    )
    assert result.returncode == 0, result.stderr

    actual = golden.normalise(json.loads(result.stdout)["violations"], root)
    expected = [v for v in golden.load_expected(project, "cca")["violations"] if v["principle"] in _PRINCIPLES]
    diff = golden.compare(actual, expected)
    assert not diff, "\n".join(diff)
    assert actual == expected
