#!/usr/bin/env python3
"""Local AI utilities — thin shim over shared model_utils."""

from pathlib import Path

from lib.ai import model_utils as _lib
from lib.ai.model_utils import (  # noqa: F401
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
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


class _ModelCache:
    """SSA's per-file model-result cache, handed to the AI client. SSA's checkers take no cache_dir."""

    def get(self, file_path: Path, prompt_name: str, max_age_days: int = 7) -> list[dict] | None:
        from .cache import get_cached

        return get_cached(file_path, prompt_name, max_age_days=max_age_days)

    def set(self, file_path: Path, prompt_name: str, results: list[dict]) -> None:
        from .cache import set_cached

        set_cached(file_path, prompt_name, results)


# Read on every call, so a test can switch it off with patch.object(model_utils, "CACHE", None)
CACHE: "_lib.ModelCache | None" = _ModelCache()


def analyze_file_with_model(*args, **kwargs):
    kwargs.setdefault("cache", CACHE)
    return _lib.analyze_file_with_model(*args, **kwargs)


async def analyze_files_async(*args, **kwargs):
    kwargs.setdefault("cache", CACHE)
    return await _lib.analyze_files_async(*args, **kwargs)


def analyze_files_parallel(*args, **kwargs):
    kwargs.setdefault("cache", CACHE)
    return _lib.analyze_files_parallel(*args, **kwargs)
