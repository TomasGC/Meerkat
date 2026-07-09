from pathlib import Path
import pytest


def pytest_collection_modifyitems(items):
    """Auto-mark tests by their subdirectory tier."""
    for item in items:
        parts = set(Path(str(item.fspath)).parts)
        if "units" in parts:
            item.add_marker(pytest.mark.units)
        if "integration-mocks" in parts:
            item.add_marker(pytest.mark.integration_mocks)
        if "integration-reals" in parts:
            item.add_marker(pytest.mark.integration_reals)
        if "e2e" in parts:
            item.add_marker(pytest.mark.e2e)
