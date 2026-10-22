"""Every SSA prompt has a live prompt case (#5), and every case is well formed."""

from pathlib import Path

from lib.testing import live_prompt

TESTS = Path(__file__).parents[1]


def test_every_prompt_has_a_well_formed_live_case():
    cases = live_prompt.load_cases(TESTS / "fixtures" / "integration_real" / "prompts")
    prompts = {p.stem for p in (TESTS.parent / "scripts" / "prompts" / "local").glob("*.prompt")}

    assert {c.prompt for c in cases} == prompts
