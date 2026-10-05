"""Golden fixture projects — full CCA pipeline with recorded AI responses replayed.

Every mechanical pass runs for real; only lib.ai.model_utils.call_model_async is
replaced. Regenerate with scripts/cli/update_golden.py --agent cca.
"""

import pytest
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


# Projects without code (sql_project) make no AI call, so there is no cache to serve
@pytest.mark.parametrize("project", golden.code_project_names())
def test_second_run_is_served_from_cache(project, tmp_path):
    cache = tmp_path / "cache"
    first = golden.run_agent(project, "cca", cache_dir=cache)
    second = golden.run_agent(project, "cca", cache_dir=cache, strict_unused=False)

    root = golden.project_path(project)
    assert golden.normalise(second["violations"], root) == golden.normalise(first["violations"], root)
    assert second["ai_calls"] == 0
    assert second["cache"]["total"] > 0
    assert second["cache"]["hits"] == second["cache"]["total"]
