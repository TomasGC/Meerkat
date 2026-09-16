# Tests - Meerkat

4-tier test structure for all Python scripts and agents.

---

## Tiers

| Tier | Directory | Marker | What |
|------|-----------|--------|------|
| Unit | `tests/unit/` | `units` | Pure in-process, no I/O, all mocked |
| Integration-mocks | `tests/integration/mock/` | `integration_mocks` | Mocked subprocess/tools |
| Integration-reals | `tests/integration/real/` | `integration_reals` | Live Ollama or real filesystem |
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
    unit/test_library_analyzer.py
    integration/mock/test_library_analyzer.py
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
│   │   ├── unit/            # 414 tests — checkers/_utils, 4 gap checkers (7 each), models from_dict, cache, parse_test_files, etc.
│   │   ├── integration/mock/ # 47 tests — library_analyzer, analyze_library_branches, 4 gap checkers (1 each)
│   │   ├── integration/real/ # 30 tests — real local AI required (skipped without a server)
│   │   └── e2e/             # 36 tests — parallel_analyzer, orchestrate, collect_coverage, diff_analysis, cache lifecycle
│   ├── security-safety-analyzer/
│   │   └── scripts/tests/
│   │       ├── conftest.py
│   │       ├── unit/            # 340 tests — 10 checkers, hybrid driver, dedup, cache, file_utils, orchestrate
│   │       ├── integration/mock/ # 28 tests — real filesystem, AI mocked at two seams (checker vs hybrid driver)
│   │       ├── integration/real/ # 25 tests — prompt slot rendering (no server) + live AI per checker
│   │       └── e2e/             # 10 tests — orchestrate.py CLI, output shaping flags
│   ├── clean-code-analyzer/
│   │   ├── scripts/tests/
│   │   │   ├── pytest.ini
│   │   │   ├── conftest.py
│   │   │   ├── unit/            # 464 tests — checkers, model_utils, cache, file_utils, orchestrate, prompts
│   │   │   ├── integration/mock/ # 17 tests — mocked Ollama, real filesystem/cache
│   │   │   ├── integration/real/ # real Ollama (devstral required)
│   │   │   └── e2e/             # full orchestrate.py CLI against fixture directories
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
    ├── cli/agents/task_monitor/tests/conftest.py + units/
    ├── cli/skills/analyze_commit/tests/conftest.py + units/
    ├── common/tests/conftest.py + units/
    └── common/cli/tests/conftest.py + units/
```

---

## Important: common Namespace Collision

`agents/black-box-analyzer/scripts/common/`, `agents/clean-code-analyzer/scripts/common/`, `agents/security-safety-analyzer/scripts/common/`, and `scripts/common/` are four independent packages.
Python's import cache will find whichever is on sys.path first.

**Rule**: Always run BBA, CCA, and scripts tests in **separate pytest invocations**.

```bash
# OK
pytest agents/black-box-analyzer/tests -m units
pytest scripts/cli/tests -m units
cd agents/clean-code-analyzer/scripts && python -m pytest tests/unit/ -q
cd agents/security-safety-analyzer/scripts && python -m pytest tests/unit/ -q

# NOT OK (common collision)
pytest agents/black-box-analyzer/tests scripts/cli/tests -m units
pytest agents/clean-code-analyzer/scripts/tests agents/black-box-analyzer/tests -m units

```

**Note**: Always run from `agents/clean-code-analyzer/scripts/` as the working directory (to avoid `common` namespace collision).

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

---

## Cache Isolation (BBA)

`agents/black-box-analyzer/tests/conftest.py` has an autouse `isolated_cache_dir`
fixture that sets `BBA_CACHE_DIR` to a per-session tmp directory.

Set as an **environment variable**, not a monkeypatched attribute: the e2e tests
run `parallel_analyzer.py` through `subprocess.run`, which cannot see a patched
attribute but does inherit the env. Without it, tests write into the real
`~/.cache/black-box-analyzer`.

`common/cache.py` reads it lazily via `_cache_home()` on every call — capturing it
at import time would break subprocess tests that set it after import.
