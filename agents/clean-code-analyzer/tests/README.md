# Test Suite

## Run tiers

    # Unit only (fast, no deps)
    pytest scripts/tests/unit/ -m unit

    # Integration with mocks
    pytest scripts/tests/integration/mock/ -m integration_mock

    # Integration real (needs Ollama running)
    pytest scripts/tests/integration/real/ -m integration_real

    # E2E (needs Docker)
    pytest scripts/tests/e2e/ -m e2e

    # All except Docker/real Ollama
    pytest scripts/tests/ -m "not e2e and not integration_real"

    # Everything
    pytest scripts/tests/
