"""Verify every prompt template renders with the slots its callers actually supply.

No AI server needed. Guards against the class of bug where a template references
a slot that analyze_files_parallel never provides, which raises KeyError at runtime
and silently produces zero AI findings.
"""

from pathlib import Path

import pytest

from lib.ai.model_utils import VERIFIER_PROMPTS
from ssa.model_utils import PROMPTS_DIR

# Slots supplied by analyze_files_parallel for every call
_BASE_SLOTS = {"language": "python", "source": "x = 1\n"}

# Extra slots supplied per prompt by the checker that owns it
_KNOWN_FINDINGS = {"known_findings": "- line 1: example"}
_EXTRA_SLOTS = {
    "security": _KNOWN_FINDINGS,
    "prompt_injection": _KNOWN_FINDINGS,
    "concurrency": _KNOWN_FINDINGS,
    "crash_bugs": _KNOWN_FINDINGS,
    "crypto": _KNOWN_FINDINGS,
    "deserialization": _KNOWN_FINDINGS,
    "misconfiguration": _KNOWN_FINDINGS,
    "resource_leaks": _KNOWN_FINDINGS,
    "sensitive_data": _KNOWN_FINDINGS,
}


def _prompt_files() -> list[Path]:
    # verify.prompt is the yes/no second opinion (#5), not an analysis prompt: no {known_findings}-
    # style schema, no JSON array answer, slots source/line/claim instead.
    return sorted(p for p in PROMPTS_DIR.glob("*.prompt") if p.stem not in VERIFIER_PROMPTS)


def test_prompts_directory_is_not_empty():
    assert _prompt_files(), f"no .prompt files found in {PROMPTS_DIR}"


@pytest.mark.parametrize("prompt_file", _prompt_files(), ids=lambda p: p.stem)
def test_prompt_renders_with_supplied_slots(prompt_file):
    """Template formats cleanly with base slots plus the owner checker's extras."""
    template = prompt_file.read_text(encoding="utf-8")
    slots = dict(_BASE_SLOTS)
    slots.update(_EXTRA_SLOTS.get(prompt_file.stem, {}))

    try:
        rendered = template.format(**slots)
    except KeyError as exc:
        pytest.fail(
            f"{prompt_file.name} references slot {exc} which no caller supplies. " f"Available slots: {sorted(slots)}"
        )
    except IndexError:
        pytest.fail(f"{prompt_file.name} has an unescaped brace; use {{{{ and }}}} for literals")

    assert rendered.strip()
    assert "{" not in rendered.replace("{{", "").replace("}}", "") or "}" in rendered


@pytest.mark.parametrize("prompt_file", _prompt_files(), ids=lambda p: p.stem)
def test_prompt_requests_json_array(prompt_file):
    """Every prompt must ask for a JSON array, since extract_json_array parses the reply."""
    content = prompt_file.read_text(encoding="utf-8")
    assert "JSON array" in content
    assert "Return []" in content
