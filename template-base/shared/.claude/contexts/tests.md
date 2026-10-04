# Tests - [Project Name]

4-tier test structure for this project.

---

## Tiers

| Tier | Directory | Marker | What |
|------|-----------|--------|------|
| Unit | `tests/unit/` | `unit` | In-process, external calls mocked |
| Integration-mock | `tests/integration_mock/` | `integration_mock` | Real filesystem, mocked subprocess/external tools |
| Integration-real | `tests/integration_real/` | `integration_real` | Live services or real external tools |
| E2E | `tests/e2e/` | `e2e` | Full process execution |

The directory name is the marker name; the root `conftest.py` applies it. Test data lives in
`tests/fixtures/` (one subdirectory per tier that uses it, when useful), never inside a tier directory.

---

## Co-location Rule

Each component keeps its tests next to its source, in one `tests/` tree:

```
src/feature_a/
├── feature_a.py
└── tests/
    ├── conftest.py
    ├── unit/test_feature_a.py
    ├── integration_mock/test_feature_a.py
    ├── integration_real/
    ├── e2e/test_feature_a.py
    └── fixtures/
```

---

## pytest.ini

One file, at the repository root:

```ini
[pytest]
testpaths =
    src/feature_a/tests
    src/feature_b/tests

markers =
    unit: in-process tests, external calls mocked
    integration_mock: mocked subprocess/tools
    integration_real: real services or real external tools
    e2e: full process execution
```

---

## Root conftest.py

Marks each test with the tier directory right under its `tests/` — no tier marks in test files:

```python
from pathlib import Path
import pytest

_TIERS = ("unit", "integration_mock", "integration_real", "e2e")


def pytest_collection_modifyitems(items):
    for item in items:
        parts = Path(str(item.fspath)).parts
        for i, part in enumerate(parts[:-1]):
            if part == "tests" and parts[i + 1] in _TIERS:
                item.add_marker(getattr(pytest.mark, parts[i + 1]))
                break
```
