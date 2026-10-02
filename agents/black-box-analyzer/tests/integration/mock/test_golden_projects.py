"""Golden fixture projects — BBA's four gap checkers end to end, recorded AI responses replayed.

Every mechanical pass runs for real; only lib.ai.model_utils.call_model_async is
replaced. Regenerate with scripts/cli/update_golden.py --agent bba.
"""

import sys
from pathlib import Path

import pytest

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.testing import golden  # noqa: E402


@pytest.mark.parametrize("project", golden.project_names())
def test_output_matches_expected(project, tmp_path):
    report = golden.run_agent(project, "bba", cache_dir=tmp_path / "cache")
    expected = golden.load_expected(project, "bba")

    actual = golden.normalise(report["violations"], golden.project_path(project))
    diff = golden.compare(actual, expected["violations"])
    assert not diff, "\n".join(diff)
    assert actual == expected["violations"]
    assert report["reconciliation"] == expected["reconciliation"]


@pytest.mark.parametrize("project", golden.project_names())
def test_every_untested_file_keeps_its_mechanical_finding(project, tmp_path):
    """Both layers on every run: the server being up never removes "no test file" findings."""
    report = golden.run_agent(project, "bba", cache_dir=tmp_path / "cache")
    whole_file = {v["principle"] for v in report["violations"] if v["line"] == 0}
    assert whole_file == {"UNIT_GAP", "INTEG_MOCK_GAP", "INTEG_REAL_GAP", "E2E_GAP"}


def test_second_run_is_served_from_the_cache(tmp_path):
    cache = tmp_path / "cache"
    golden.run_agent("python_project", "bba", cache_dir=cache)
    again = golden.run_agent("python_project", "bba", cache_dir=cache, strict_unused=False)
    assert again["ai_calls"] == 0
    assert again["cache"] == {"hits": 4, "total": 4}
