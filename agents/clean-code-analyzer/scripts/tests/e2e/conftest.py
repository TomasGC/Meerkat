"""E2E conftest — reaches the configured local AI provider, whichever it is."""

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common.model_utils import (  # noqa: E402
    LOCAL_AI_HOST,
    LOCAL_AI_PORT,
    check_server_available,
)


@pytest.fixture(scope="session")
def local_ai_service():
    """Session-scoped: require the configured local AI provider to be reachable.

    The endpoint and model come from local.base_url in
    configs/local_models_config.json, so switching provider is a config edit
    rather than a test change.
    """
    if not check_server_available():
        pytest.skip(
            f"Local AI provider not reachable at {LOCAL_AI_HOST}:{LOCAL_AI_PORT}"
        )
    yield
