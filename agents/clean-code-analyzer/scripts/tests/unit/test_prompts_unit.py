"""Unit tests for prompt file structure — no Ollama required."""

import string
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
PROMPTS_OLLAMA = SCRIPTS_DIR / "prompts" / "ollama"
PROMPTS_CLAUDE = SCRIPTS_DIR / "prompts" / "claude"

PRINCIPLES = [
    "solid_analysis",
    "kiss_overengineering",
    "yagni_speculative",
    "cqrs_analysis",
    "ddd_analysis",
    "slap_analysis",
]

# Fields each ollama prompt's output schema must mention
_REQUIRED_OUTPUT_FIELDS = ["line", "severity", "suggestion", "violation"]

# Principle-specific keywords that must appear in each prompt (either dir)
_PRINCIPLE_KEYWORDS = {
    "solid_analysis": ["principle", "S/O/L/I/D", "Single Responsibility"],
    "kiss_overengineering": ["pattern", "complexity", "simple"],
    "yagni_speculative": ["pattern", "speculative", "YAGNI"],
    "cqrs_analysis": ["command", "query", "CQRS"],
    "ddd_analysis": ["domain", "entity", "DDD"],
    "slap_analysis": ["function", "abstraction", "SLAP"],
}

# Standard kwargs passed by ollama_utils: template.format(language=..., source=...)
_STANDARD_KWARGS = {"language": "python", "source": "class X: pass\n"}


# ── helpers ──────────────────────────────────────────────────────────────────


def _read(prompt_dir: Path, name: str) -> str:
    return (prompt_dir / f"{name}.prompt").read_text(encoding="utf-8")


def _placeholders(template: str) -> set[str]:
    """Return all named placeholder keys from a format-string template."""
    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(template)
        if field_name is not None
    }


# ── existence ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_exists(name):
    assert (PROMPTS_OLLAMA / f"{name}.prompt").exists(), f"Missing ollama/{name}.prompt"


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_exists(name):
    assert (PROMPTS_CLAUDE / f"{name}.prompt").exists(), f"Missing claude/{name}.prompt"


# ── non-empty ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_not_empty(name):
    assert _read(PROMPTS_OLLAMA, name).strip(), f"ollama/{name}.prompt is blank"


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_not_empty(name):
    assert _read(PROMPTS_CLAUDE, name).strip(), f"claude/{name}.prompt is blank"


# ── JSON instruction (ollama only — these must produce parseable JSON) ─────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_contains_json_instruction(name):
    content = _read(PROMPTS_OLLAMA, name)
    assert "JSON" in content, f"ollama/{name}.prompt missing JSON output instruction"


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_instructs_array_output(name):
    content = _read(PROMPTS_OLLAMA, name)
    has_array = "[]" in content or "array" in content.lower()
    assert has_array, f"ollama/{name}.prompt does not instruct array output"


# ── required output schema fields (ollama prompts) ───────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.parametrize("field", _REQUIRED_OUTPUT_FIELDS)
@pytest.mark.unit
def test_ollama_prompt_mentions_required_field(name, field):
    content = _read(PROMPTS_OLLAMA, name)
    assert field in content, f"ollama/{name}.prompt missing output field '{field}'"


# ── principle-specific keywords ───────────────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_contains_principle_keywords(name):
    content = _read(PROMPTS_OLLAMA, name)
    keywords = _PRINCIPLE_KEYWORDS[name]
    assert any(kw in content for kw in keywords), (
        f"ollama/{name}.prompt missing principle keywords (expected one of {keywords})"
    )


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_contains_principle_keywords(name):
    content = _read(PROMPTS_CLAUDE, name)
    keywords = _PRINCIPLE_KEYWORDS[name]
    assert any(kw in content for kw in keywords), (
        f"claude/{name}.prompt missing principle keywords (expected one of {keywords})"
    )


# ── valid format-string (no KeyError on standard kwargs) ─────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_format_string_valid(name):
    template = _read(PROMPTS_OLLAMA, name)
    try:
        template.format(**_STANDARD_KWARGS)
    except KeyError as exc:
        pytest.fail(f"ollama/{name}.prompt has unknown placeholder {exc}")


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_format_string_valid(name):
    template = _read(PROMPTS_CLAUDE, name)
    try:
        template.format(**_STANDARD_KWARGS)
    except KeyError as exc:
        pytest.fail(f"claude/{name}.prompt has unknown placeholder {exc}")


# ── no stray unmatched braces ─────────────────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_no_stray_braces(name):
    template = _read(PROMPTS_OLLAMA, name)
    try:
        list(string.Formatter().parse(template))
    except (ValueError, KeyError) as exc:
        pytest.fail(f"ollama/{name}.prompt has stray braces: {exc}")


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_no_stray_braces(name):
    template = _read(PROMPTS_CLAUDE, name)
    try:
        list(string.Formatter().parse(template))
    except (ValueError, KeyError) as exc:
        pytest.fail(f"claude/{name}.prompt has stray braces: {exc}")


# ── ollama vs claude placeholder parity ──────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_claude_placeholder_parity(name):
    """Both versions of the same prompt accept the same format kwargs."""
    ollama_keys = _placeholders(_read(PROMPTS_OLLAMA, name))
    claude_keys = _placeholders(_read(PROMPTS_CLAUDE, name))
    assert ollama_keys == claude_keys, (
        f"{name}.prompt placeholder mismatch — "
        f"ollama={ollama_keys}, claude={claude_keys}"
    )


# ── max length guard ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_ollama_prompt_max_length(name):
    content = _read(PROMPTS_OLLAMA, name)
    assert len(content) <= 4000, (
        f"ollama/{name}.prompt is {len(content)} chars — exceeds 4000 char limit"
    )


@pytest.mark.parametrize("name", PRINCIPLES)
@pytest.mark.unit
def test_claude_prompt_max_length(name):
    content = _read(PROMPTS_CLAUDE, name)
    assert len(content) <= 4000, (
        f"claude/{name}.prompt is {len(content)} chars — exceeds 4000 char limit"
    )
