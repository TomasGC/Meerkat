from pathlib import Path
import pytest


def pytest_collection_modifyitems(items):
    """Auto-mark tests by their subdirectory tier."""
    for item in items:
        parts = set(Path(str(item.fspath)).parts)
        if "unit" in parts:
            item.add_marker(pytest.mark.units)
        if "mock" in parts and "integration" in parts:
            item.add_marker(pytest.mark.integration_mocks)
        if "real" in parts and "integration" in parts:
            item.add_marker(pytest.mark.integration_reals)
        if "e2e" in parts:
            item.add_marker(pytest.mark.e2e)
