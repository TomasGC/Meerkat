#!/usr/bin/env python3
"""Local AI utilities — thin shim over shared model_utils."""

from pathlib import Path

from lib.ai.model_utils import (  # noqa: F401
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
    analyze_file_with_model,
    analyze_files_async,
    analyze_files_parallel,
    call_model,
    call_model_async,
    call_model_multi,
    check_server_available,
    extract_json_array,
    extract_json_object,
    run_prompt,
    split_into_chunks,
)

_AGENT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = _AGENT_DIR / "prompts" / "local"
CLAUDE_PROMPTS_DIR = _AGENT_DIR / "prompts" / "claude"


def get_claude_fallback_prompt(name: str, **kwargs) -> str | None:
    """Return formatted Claude fallback prompt when local AI unavailable."""
    prompt_file = CLAUDE_PROMPTS_DIR / f"{name}.prompt"
    try:
        return prompt_file.read_text(encoding="utf-8").format(**kwargs)
    except FileNotFoundError:
        return None
    except KeyError:
        return prompt_file.read_text(encoding="utf-8")
