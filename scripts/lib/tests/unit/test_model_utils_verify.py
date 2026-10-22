"""Unit tests for the verifier of lib.ai.model_utils.analyze_files_parallel (#5).

When the prompts directory holds a verify.prompt, every finding is put to the model
again as a closed question and dropped on a clear NO. call_model_async is replaced
per test; no server needed.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

import lib.ai.model_utils as mu
from lib import paths

_FINDINGS = '[{"line": 1, "description": "real"}, {"line": 2, "description": "imagined"}]'
_VERIFY = "Claim about line {line}: {claim}\nFile:\n{source}\nAnswer with one word: YES or NO."

_REAL_VERIFY_PROMPTS = [
    paths.AGENTS / "clean-code-analyzer" / "scripts" / "prompts" / "local" / f"{mu.VERIFY_PROMPT}.prompt",
    paths.AGENTS / "security-safety-analyzer" / "scripts" / "prompts" / "local" / f"{mu.VERIFY_PROMPT}.prompt",
]


def _prompts(tmp_path: Path, verifier: bool) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "p.prompt").write_text("{language}\n{source}", encoding="utf-8")
    if verifier:
        (prompts / "verify.prompt").write_text(_VERIFY, encoding="utf-8")
    return prompts


def _analyze(tmp_path: Path, prompts: Path, verify_answer) -> tuple[list[dict], list[str]]:
    source = tmp_path / "m.py"
    source.write_text("x = 1\n", encoding="utf-8")
    prompts_seen: list[str] = []

    async def model(prompt, role="analyzer", timeout=None):
        prompts_seen.append(prompt)
        if "YES or NO" not in prompt:
            return _FINDINGS
        return verify_answer(prompt)

    with patch.object(mu, "call_model_async", side_effect=model):
        items = mu.analyze_files_parallel([source], "python", prompt_name="p", prompts_dir=prompts, no_cache=True)
    return items, prompts_seen


def test_a_finding_the_verifier_answers_no_to_is_dropped(tmp_path):
    items, seen = _analyze(tmp_path, _prompts(tmp_path, True), lambda p: "NO." if "imagined" in p else "YES")

    assert [i["description"] for i in items] == ["real"]
    assert len(seen) == 3
    assert "Claim about line 2: imagined\nFile:\nx = 1\n" in seen[2] or "Claim about line 2: imagined" in "".join(seen)


def test_without_a_verify_prompt_the_model_is_asked_once(tmp_path):
    items, seen = _analyze(tmp_path, _prompts(tmp_path, False), lambda p: pytest.fail("verifier called"))

    assert len(items) == 2
    assert len(seen) == 1


@pytest.mark.parametrize("answer", [None, "", "maybe", RuntimeError("server gone")])
def test_a_missing_or_unclear_verdict_keeps_the_finding(tmp_path, answer):
    def verify(prompt):
        if isinstance(answer, BaseException):
            raise answer
        return answer

    items, _ = _analyze(tmp_path, _prompts(tmp_path, True), verify)

    assert len(items) == 2


@pytest.mark.parametrize(
    ("item", "claim"),
    [
        ({"principle": "S", "violation": "two jobs"}, "[S] two jobs"),
        ({"vulnerability_type": "IDOR", "description": "no owner check"}, "[IDOR] no owner check"),
        ({"function": "f", "reason": "has branches"}, "has branches"),
    ],
)
def test_claim_names_the_finding_whatever_its_field_names(item, claim):
    assert mu._claim(item) == claim


@pytest.mark.parametrize(
    ("answer", "keep"), [("NO", False), ("no.", False), ("**NO**", False), ("YES", True), ("Nothing", True)]
)
def test_verdict_drops_only_a_clear_no(answer, keep):
    assert mu._verdict(answer) is keep


@pytest.mark.parametrize("prompt_file", _REAL_VERIFY_PROMPTS, ids=lambda p: p.parents[2].name)
def test_the_shipped_verify_prompt_renders_and_asks_for_one_word(prompt_file):
    """Each agent's real verify.prompt formats with the slots analyze_files_async supplies."""
    template = prompt_file.read_text(encoding="utf-8")

    rendered = template.format(source="x = 1\n", line=1, claim="[S] two jobs", language="python")

    assert "YES" in rendered and "NO" in rendered
