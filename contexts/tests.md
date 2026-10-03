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
│                                                        # + --import-mode=importlib (duplicate package names across trees)
│
├── agents/
│   ├── black-box-analyzer/tests/
│   │   ├── conftest.py
│   │   ├── unit/            # checkers/_utils + run_gap_checker, 4 gap checkers (7 each), detect_project_language, models from_dict, cache, LibraryAnalyzer routing
│   │   ├── integration/mock/ # library_analyzer, analyze_library_branches, 4 gap checkers, test_golden_projects.py (replayed AI)
│   │   │                     # unit + mock + e2e = 524
│   │   ├── integration/real/ # 30 tests — 20 universal detection over fixtures/ (no AI), model_utils, open_report
│   │   │   └── fixtures/     # 10 minimal projects, one per detected type — see note below
│   │   └── e2e/             # parallel_analyzer, orchestrate (incl. --gaps), collect_coverage, diff_analysis, cache lifecycle
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
│   │   │   ├── unit/            # checkers (via lib.engine.hybrid), model_utils, orchestrate shim, prompts
│   │   │   ├── integration/mock/ # unit + mock = 526 — incl. test_golden_projects.py (replayed AI) and cache round-trip
│   │   │   ├── integration/real/ # live AI: checkers, multi-language, test_engine_real.py (cache + reconciliation invariant)
│   │   │   ├── e2e/             # 15 — orchestrate.py CLI, real-git incremental modes, --clear-cache, test_golden_cli.py
│   │   │   └── test_*.py        # tests at tests/ root, outside the 4 tiers — cache, checkers, discovery, orchestrate
│   └── tests/
│       └── integration-reals/  # cross-agent Ollama tests (not BBA-specific)
│           ├── test_agents.py
│           └── test_ollama_integration.py
│
└── scripts/
    ├── tests/conftest.py + e2e/ + integration-reals/
    ├── cli/tests/conftest.py + units/ + integration-mocks/ + integration-reals/
    ├── cli/agents/task_monitor/tests/units/    # no conftest — in root testpaths
    ├── lib/tests/conftest.py + units/      # 251 tests — language_config, discovery, orchestrator (per-language runs), dedup,
    │                                       # hybrid ai_filter, model_config, model_utils (failed-call tracking), golden runner
    └── lib/cli/tests/conftest.py + units/

skills/
└── search-tech/scripts/tests/       # 113 tests — cache, logger, models, utils
                                     # package: search_tech/ (was common/)
```

---

## One Invocation for Every Suite (#21)

Every suite runs from `~/.claude` in one pytest invocation:

```bash
cd ~/.claude
python -m pytest -q -m "not integration_reals" \
  --ignore=agents/security-safety-analyzer/scripts/tests/integration/mock/test_orchestrate.py \
  --deselect "agents/clean-code-analyzer/scripts/tests/e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates"
```

What makes it work, and what keeps it working:
- **Each agent owns one uniquely named package**: `cca/`, `ssa/`, `bba/` under the agent's `scripts/`, and
  `search_tech/` for the skill. Nothing importable is called `common`, `checkers` or `orchestrate` at top level.
  `scripts/orchestrate.py` is a three-line CLI wrapper, never imported by tests.
- **No `__init__.py` in test trees, nor in the agents' `scripts/` dirs.** With `--import-mode=importlib`, pytest
  names a test module after its path from the rootdir, so two `tests/unit/test_cache.py` stay distinct. An
  `__init__.py` makes pytest name it after the package instead (`scripts.tests.conftest`), and two agents collide.
- Tests import `from .conftest` nowhere: shared test switches are markers (`@pytest.mark.live_ai`) that a
  conftest turns into skips.
- The AI client holds no cache state: each agent's `model_utils` shim passes its own `CACHE` on every call, so
  loading three agents in one process cannot make one read another's cache.

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

`bba/cache.py` reads it lazily via `_cache_home()` on every call — capturing it
at import time would break subprocess tests that set it after import.

---

## Detection Fixtures (BBA real tier)

`tests/integration/real/fixtures/` holds ten minimal projects, one per detected
project type. Each is written against the exact regexes its analyzer uses, so a
fixture edit is a contract change:

- Every fixture is detected on a **strong** signal (file marker or manifest
  framework), never the ≥2-pattern fallback — pattern counts are a safety net,
  not the thing under test.
- No fixture source may live under `build/`, `dist/`, `bin/` or any other
  `EXCLUDED_DIRS` entry: `walk_files` would skip it.
- No fixture file may be named `test_*.py` — pytest would collect it.
- `sql_project` deliberately carries no manifest. `find_project_root` stops at
  the enclosing `.git`, so it resolves to the fixture itself rather than an
  ancestor.
- `hybrid_project` resolves to language **java** on purpose: `count_endpoints`
  globs only `*.kt` for Kotlin and `APIAnalyzer` never walks `*.kt`, so a Kotlin
  controller yields zero endpoints and no `REST_API`. Its Activity sits in
  `app/` so no top-level `*.kt` wins the language vote.

---

## Golden Fixtures (CCA + SSA + BBA gaps)

`~/.claude/fixtures/` is shared test data, owned by no agent:

- `fixtures/projects/<p>/` — `python_project`, `go_project`, `kotlin_project`: **source only**, seeded with
  clean-code and security issues on purpose, and no tests at all (every file is a gap in every BBA tier).
  Never imported or run. `python_project/deploy.yaml` is a deliberate Kubernetes manifest (#20): only the
  SSA checkers that accept data files see it, under language `yaml`; CCA and BBA goldens must not change.
- `fixtures/projects/sql_project/` (#42) — one T-SQL and one PostgreSQL file, no code: SSA's five SQL checkers and
  CCA comments/naming report on it, BBA reports nothing. Tests that need code (cache round-trip, gap tiers)
  parametrize over `golden.code_project_names()`, not `project_names()`.
- `fixtures/golden/<p>/expected/<agent>.json` — every issue the agent must find, all fields compared
  (`principle, file, line, severity, message, suggestion`, posix paths), plus per-checker reconciliation counts.
- `fixtures/golden/<p>/ai_responses/<agent>/<prompt>.json` — recorded model responses, replayed at
  `lib.ai.model_utils.call_model_async` by `scripts/lib/testing/golden.py`. An unmatched call, a missing
  response or an unused response is an error — a silent `[]` can never pass.

Rules:
- Metadata stays out of `projects/`: a file there is input, and any checker accepting its kind scans it.
- Keep an AI response more than 3 lines from a mechanical finding in the same file unless it is meant to be
  dropped as a duplicate: reconciliation's proximity window is ±3 lines (whole-file line-0 findings excepted).
- Test-file detection is a substring match on the file name (`test`, `spec`, `fixture`, `mock`, `migration`):
  a source named `untested.py` or `contest.py` is treated as a test. Pick fixture names accordingly.
- No `__init__.py`, no `test_*` file, no directory name from `language_config.skip_dirs()` under `fixtures/`.
- Fake secrets must not match a real provider format (no `sk_live_`, `AKIA`, `ghp_`): push protection.
- `.gitignore` needs `!/fixtures/projects/`: the unanchored `projects/` rule would ignore it.
- Regenerating expected files (`scripts/cli/update_golden.py`) snapshots whatever the code does — hand-check
  every changed record as a genuine intended issue before committing.

---

## Known Environmental Exclusions

With the local model mostly offloaded to CPU, two tests can exceed their limits; exclude them, don't "fix" them:
- SSA `tests/integration/mock/test_orchestrate.py` — runs a full orchestrate.py against the live AI with no timeout
  (`--ignore` it). Despite the tier name it is not mocked.
- CCA `e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates` — 300s limit; passes in ~193s
  when the GPU is free. The node id has no `tests/` prefix: CCA's rootdir is `scripts/tests`.

## Worktrees and Clones Are Not Faithful

Checkers and shims insert `~/.claude/scripts` as the shared-library path, so tests run in a git worktree import
the **main checkout's** `lib/`, not the worktree's. Compare a worktree run against pristine `main` in a worktree,
never against the main checkout.

A fresh clone anywhere other than `~/.claude` is worse: `scripts/lib/testing/golden.py` resolves agents under
`~/.claude/agents/`, so a golden test run from the clone imports the clone's agent package and then the real
checkout's agent, and stops with "`cca` already imported from …, not from …". To check what a fresh
clone contains (#34: prompt templates), inspect the files directly instead of running the suites there. A CI
runner (#2) checks out elsewhere too, so the hardcoded path has to go before CI can run these tests.

## Prompt Templates Are Tracked

`.gitignore`'s `*local*` rule (personal files) would also hide `agents/*/scripts/prompts/local/`, the local-AI
prompt templates; `!**/prompts/local/` re-includes them (#34). A new prompt file there is tracked like any source
file — no `git add -f` needed.
