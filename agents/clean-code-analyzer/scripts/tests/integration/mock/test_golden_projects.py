"""Golden fixture projects — full CCA pipeline with recorded AI responses replayed.

Every mechanical pass runs for real; only lib.ai.model_utils.call_model_async is
replaced. Regenerate with scripts/cli/update_golden.py --agent cca.
"""

import sys
from pathlib import Path

import pytest

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.testing import golden  # noqa: E402

PROJECTS = golden.project_names()


@pytest.mark.parametrize("project", PROJECTS)
def test_output_matches_expected(project, tmp_path):
    report = golden.run_agent(project, "cca", cache_dir=tmp_path / "cache")
    expected = golden.load_expected(project, "cca")

    actual = golden.normalise(report["violations"], golden.project_path(project))
    diff = golden.compare(actual, expected["violations"])
    assert not diff, "\n".join(diff)
    assert actual == expected["violations"]
    assert report["reconciliation"] == expected["reconciliation"]


@pytest.mark.parametrize("project", PROJECTS)
def test_second_run_is_served_from_cache(project, tmp_path):
    cache = tmp_path / "cache"
    first = golden.run_agent(project, "cca", cache_dir=cache)
    second = golden.run_agent(project, "cca", cache_dir=cache, strict_unused=False)

    root = golden.project_path(project)
    assert golden.normalise(second["violations"], root) == golden.normalise(first["violations"], root)
    assert second["ai_calls"] == 0
    assert second["cache"]["total"] > 0
    assert second["cache"]["hits"] == second["cache"]["total"]
