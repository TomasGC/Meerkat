#!/usr/bin/env python3
"""Local AI utilities — thin shim over shared model_utils."""

import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.ai.model_utils import (  # noqa: F401
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
    check_server_available,
    call_model,
    call_model_async,
    call_model_multi,
    run_prompt,
    analyze_file_with_model,
    analyze_files_async,
    analyze_files_parallel,
    extract_json_array,
    extract_json_object,
    split_into_chunks,
)

_AGENT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = _AGENT_DIR / "prompts" / "local"
CLAUDE_PROMPTS_DIR = _AGENT_DIR / "prompts" / "claude"
