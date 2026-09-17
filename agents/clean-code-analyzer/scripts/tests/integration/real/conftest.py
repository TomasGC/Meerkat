"""Conftest for real-provider integration tests — skip if the configured server is down."""

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).parent.parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common.model_utils import (  # noqa: E402
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
    check_server_available,
)

ollama_skip = pytest.mark.skipif(
    not check_server_available(),
    reason=f"Local AI provider not reachable at {LOCAL_AI_HOST}:{LOCAL_AI_PORT}",
)
