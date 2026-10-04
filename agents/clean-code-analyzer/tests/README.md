# Test Suite

Layout and tier rules: `contexts/tests.md`. Run from `agents/clean-code-analyzer/`:

    # Unit (in-process, AI mocked)
    python -m pytest tests/unit/

    # Integration with mocks, incl. golden tests (replayed AI)
    python -m pytest tests/integration_mock/

    # Integration real (needs the configured local AI server)
    python -m pytest tests/integration_real/

    # E2E (subprocess against orchestrate.py)
    python -m pytest tests/e2e/

    # Everything except the live-AI tier
    python -m pytest tests/ -m "not integration_real"

Sample projects for the e2e tier are in `tests/fixtures/e2e/`.
