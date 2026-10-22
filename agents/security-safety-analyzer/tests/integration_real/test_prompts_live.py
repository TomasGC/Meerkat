"""Live prompt cases (#5): each AI prompt finds its seeded issue and stays quiet once it is fixed."""

import importlib
from pathlib import Path

import pytest

from lib.testing import live_prompt
from ssa.model_utils import check_server_available

CASES = live_prompt.load_cases(Path(__file__).parents[1] / "fixtures" / "integration_real" / "prompts")
PROMPTS = Path(__file__).parents[2] / "scripts" / "prompts" / "local"

pytestmark = pytest.mark.live_ai


@pytest.fixture(scope="module", autouse=True)
def _server():
    if not check_server_available():
        pytest.skip("local AI server not reachable")


def _run(case: live_prompt.Case, variant: str) -> live_prompt.LiveRun:
    return live_prompt.run_case(case, variant, importlib.import_module(f"ssa.checkers.{case.checker}").run)


@pytest.mark.parametrize("variant", ["dirty", "clean"])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_answer_has_the_fields_the_prompt_asks_for(case, variant):
    live_prompt.assert_answer_has_the_fields(_run(case, variant), PROMPTS / f"{case.prompt}.prompt")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_dirty_file_gets_an_ai_finding_on_the_seeded_issue(case):
    live_prompt.assert_detects(case, _run(case, "dirty"))


@pytest.mark.parametrize("case", live_prompt.clean_params(CASES), ids=lambda c: c.name)
def test_clean_twin_gets_no_ai_finding_where_the_issue_was_fixed(case):
    live_prompt.assert_quiet_once_fixed(case, _run(case, "clean"))
