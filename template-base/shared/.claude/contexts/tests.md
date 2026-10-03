# Tests - [Project Name]

4-tier test structure for this project.

---

## Tiers

| Tier | Directory | Marker | What |
|------|-----------|--------|------|
| Unit | `tests/units/` | `units` | Pure in-process, no I/O, all mocked |
| Integration-mocks | `tests/integration-mocks/` | `integration_mocks` | Mocked subprocess/external tools |
| Integration-reals | `tests/integration-reals/` | `integration_reals` | Live services or real filesystem |
| E2E | `tests/e2e/` | `e2e` | Full process execution |

Markers applied automatically by `conftest.py` based on directory name.

---

## Co-location Rule

Tests live **next to their source**, not in a central mirror tree:

```
src/
├── feature_a.py
└── tests/
    ├── conftest.py
    ├── units/test_feature_a.py
    ├── integration-mocks/test_feature_a_mock.py
    └── e2e/test_feature_a_e2e.py
```

---

## pytest.ini

```ini
[pytest]
testpaths =
    src/tests
    src/feature_a/tests
    src/feature_b/tests

markers =
    units: pure in-process tests (no I/O, all mocked)
    integration_mocks: mocked subprocess/tools
    integration_reals: real services or real filesystem
    e2e: full process execution
```

---

## Root conftest.py

Auto-marks tests by directory name — no boilerplate in test files:

```python
from pathlib import Path
import pytest

def pytest_collection_modifyitems(items):
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
```
