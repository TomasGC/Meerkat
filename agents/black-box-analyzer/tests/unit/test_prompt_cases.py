"""Every BBA gap prompt has a live prompt case (#5), and every case is well formed."""

from pathlib import Path

from lib.testing import live_prompt

TESTS = Path(__file__).parents[1]
# The prompts the gap checkers run through lib.engine.hybrid; the pipeline's other prompts are out of scope
GAP_PROMPTS = {"unit_gaps", "integ_mock_gaps", "integ_real_gaps", "e2e_gaps"}


def test_every_gap_prompt_has_a_well_formed_live_case():
    cases = live_prompt.load_cases(TESTS / "fixtures" / "integration_real" / "prompts")

    assert {c.prompt for c in cases} == GAP_PROMPTS
    assert all((TESTS.parent / "scripts" / "prompts" / "local" / f"{p}.prompt").exists() for p in GAP_PROMPTS)
