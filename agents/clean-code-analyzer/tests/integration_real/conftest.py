"""Conftest for real-provider integration tests — skip if the configured server is down."""

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from cca.model_utils import (  # noqa: E402
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
    check_server_available,
)



def pytest_collection_modifyitems(config, items):
    """Skip every `@pytest.mark.live_ai` test here when the configured server is down."""
    here = Path(__file__).parent
    marked = [i for i in items if i.get_closest_marker("live_ai") and Path(str(i.fspath)).is_relative_to(here)]
    if marked and not check_server_available():
        skip = pytest.mark.skip(reason=f"Local AI provider not reachable at {LOCAL_AI_HOST}:{LOCAL_AI_PORT}")
        for item in marked:
            item.add_marker(skip)
