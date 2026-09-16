from pathlib import Path
import pytest

# Two directory naming conventions coexist: agents use unit/ + integration/mock/,
# scripts use units/ + integration-mocks/. Both map to the same tier markers.
_TIER_DIRS = {
    "unit": "units",
    "units": "units",
    "integration-mocks": "integration_mocks",
    "integration-reals": "integration_reals",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(items):
    """Auto-mark tests by their subdirectory tier."""
    for item in items:
        parts = set(Path(str(item.fspath)).parts)
        for directory, marker in _TIER_DIRS.items():
            if directory in parts:
                item.add_marker(getattr(pytest.mark, marker))
        if "integration" in parts and "mock" in parts:
            item.add_marker(pytest.mark.integration_mocks)
        if "integration" in parts and "real" in parts:
            item.add_marker(pytest.mark.integration_reals)
