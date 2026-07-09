# Tests - Meerkat

4-tier test structure for all Python scripts and agents.

---

## Tiers

| Tier | Directory | Marker | What |
|------|-----------|--------|------|
| Unit | `tests/units/` | `units` | Pure in-process, no I/O, all mocked |
| Integration-mocks | `tests/integration-mocks/` | `integration_mocks` | Mocked subprocess/tools |
| Integration-reals | `tests/integration-reals/` | `integration_reals` | Live Ollama or real filesystem |
| E2E | `tests/e2e/` | `e2e` | `subprocess.run` on actual scripts |

Markers applied automatically by root `conftest.py` based on directory name.

---

## Co-location Rule

Tests live **next to their source**, not in a central mirror tree:

```
scripts/cli/format_code.py
scripts/cli/tests/
    conftest.py
    units/test_format_code.py
    integration-mocks/test_format_code_mock.py

agents/black-box-analyzer/scripts/library_analyzer.py
agents/black-box-analyzer/tests/
    conftest.py
    units/test_library_analyzer.py
    integration-mocks/test_library_analyzer.py
    e2e/test_end_to_end.py
```

---

## Test Locations

```
~/.claude/
├── conftest.py                                          # root: auto-mark by dir
├── pytest.ini                                           # testpaths + markers
│
├── agents/
│   ├── black-box-analyzer/tests/
│   │   ├── conftest.py
│   │   ├── units/
│   │   ├── integration-mocks/
│   │   ├── integration-reals/
│   │   └── e2e/
│   └── tests/
│       └── integration-reals/  # cross-agent Ollama tests (not BBA-specific)
│           ├── test_agents.py
│           └── test_ollama_integration.py
│
└── scripts/
    ├── tests/conftest.py + e2e/ + integration-reals/
    ├── cli/tests/conftest.py + units/ + integration-mocks/ + integration-reals/
    ├── cli/agents/ci_fix_proposer/tests/conftest.py + units/
    ├── cli/agents/code_analyzer/tests/conftest.py + units/
    ├── cli/skills/analyze_commit/tests/conftest.py + units/
    ├── common/tests/conftest.py + units/
    └── common/cli/tests/conftest.py + units/
```

---

## Important: common Namespace Collision

`agents/black-box-analyzer/scripts/common/` and `scripts/common/` are two different packages.
Python's import cache will find whichever is on sys.path first.

**Rule**: Always run BBA tests and scripts tests in **separate pytest invocations**.

```bash
# OK
pytest agents/black-box-analyzer/tests -m units
pytest scripts/cli/tests -m units

# NOT OK (common collision)
pytest agents/black-box-analyzer/tests scripts/cli/tests -m units
```

---

## conftest.py Pattern

Each test directory has a `conftest.py` that adds the right source root to `sys.path`:

```python
# agents/black-box-analyzer/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# scripts/cli/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # → scripts/

# scripts/tests/conftest.py (uses append, not insert — avoids clobbering BBA path)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
```
