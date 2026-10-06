"""Golden fixture projects — full SSA pipeline with recorded AI responses replayed.

Every mechanical pass runs for real; only lib.ai.model_utils.call_model_async is
replaced. Regenerate with scripts/cli/update_golden.py --agent ssa.
SSA's orchestrator passes no cache_dir to its checkers, so there is no cache round-trip test.
"""

import pytest

from lib.testing import golden  # noqa: E402


@pytest.mark.parametrize("project", golden.project_names())
def test_output_matches_expected(project, tmp_path):
    report = golden.run_agent(project, "ssa", cache_dir=tmp_path / "cache")
    expected = golden.load_expected(project, "ssa")

    actual = golden.normalise(report["violations"], golden.project_path(project))
    diff = golden.compare(actual, expected["violations"])
    assert not diff, "\n".join(diff)
    assert actual == expected["violations"]
    assert report["reconciliation"] == expected["reconciliation"]
