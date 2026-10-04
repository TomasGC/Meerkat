# Tests - Meerkat

4-tier test structure, one layout for every component (#46).

---

## Layout Rule

```
<component>/tests/
    conftest.py          # puts the component's source root on sys.path
    unit/
    integration_mock/
    integration_real/
    e2e/
    fixtures/            # test data only; optional subdirs per tier that uses it
```

- **Components**: `agents/<NAME>`, `skills/<NAME>`, `plugins/<NAME>`, `scripts/lib`, `scripts/cli`.
  A sub-package (`scripts/lib/cli`, `scripts/cli/agents/task_monitor`) has no tests tree of its own:
  its tests live in its component's tree.
- **Directory name = marker name.** The root `conftest.py` marks every test with the tier directory right
  under its `tests/`; no test file carries a tier mark of its own. A test outside a tier directory would
  get no tier, so none exists: the four tier runs are disjoint and add up to the full collection.
- **Fixtures** live in `tests/fixtures/`, never inside a tier directory: `fixtures/integration_real/`
  (BBA's detection projects), `fixtures/e2e/` (CCA's dirty/clean sample projects).
- **Cross-cutting tests** belong to the component they exercise. Tests that drive several components at once
  live in the root `tests/<tier>/` (delegation rules, agent and skill workflows).
- **One `pytest.ini`**, at the repo root. Sub-directories inside a tier mirror the source package where it
  helps (`cca` tests: `unit/checkers/`).

## Tiers

| Tier | Directory | Marker | What |
|------|-----------|--------|------|
| Unit | `tests/unit/` | `unit` | In-process; subprocess and AI mocked, `tmp_path` allowed |
| Integration-mock | `tests/integration_mock/` | `integration_mock` | Real filesystem, mocked subprocess/tools/AI |
| Integration-real | `tests/integration_real/` | `integration_real` | Live local AI or real external tools |
| E2E | `tests/e2e/` | `e2e` | `subprocess.run` on actual scripts |

---

## Test Locations

```
~/.claude/
├── conftest.py                     # root: tier marker = tier directory name
├── pytest.ini                      # testpaths (one per component) + markers + --import-mode=importlib
│
├── agents/
│   ├── black-box-analyzer/tests/
│   │   ├── conftest.py             # sys.path → ../scripts; autouse BBA_CACHE_DIR isolation
│   │   ├── unit/                   # 418 — checkers/_utils + run_gap_checker, 4 gap checkers, detect_project_language, models, cache
│   │   ├── integration_mock/       # 55 — library_analyzer, analyze_library_branches, 4 gap checkers, test_golden_projects.py
│   │   ├── integration_real/       # 30 — 20 universal detection over fixtures/integration_real/ (no AI), model_utils, open_report
│   │   ├── e2e/                    # 39 — parallel_analyzer, orchestrate (incl. --gaps), coverage, diff_analysis, cache lifecycle
│   │   └── fixtures/integration_real/   # 10 minimal projects, one per detected type
│   ├── clean-code-analyzer/tests/
│   │   ├── conftest.py             # sys.path → ../scripts; dirty/clean project fixtures
│   │   ├── unit/                   # 595 — checkers (unit/checkers/), cache, discovery, model_utils shim, orchestrate, prompts
│   │   ├── integration_mock/       # 24 — test_golden_projects.py (replayed AI), cache round-trip, incremental, orchestrate
│   │   ├── integration_real/       # 18 — live AI: checkers, multi-language, test_engine_real.py
│   │   ├── e2e/                    # 16 — orchestrate.py CLI, real-git incremental modes, --clear-cache, test_golden_cli.py
│   │   └── fixtures/e2e/           # dirty_* / clean_* sample projects
│   └── security-safety-analyzer/tests/
│       ├── conftest.py             # sys.path → ../scripts
│       ├── unit/                   # 415 — 10 checkers, SQL rules, hybrid driver, dedup, cache, file_utils, orchestrate
│       ├── integration_mock/       # 36 — real filesystem, AI mocked at two seams; test_golden_projects.py
│       ├── integration_real/       # 25 — prompt slot rendering (no server) + live AI per checker
│       └── e2e/                    # 10 — orchestrate.py CLI, output shaping flags
│
├── skills/search-tech/tests/
│   ├── conftest.py                 # sys.path → ../scripts; sample query/result fixtures
│   └── unit/                       # 113 — cache, logger, models, aggregate, per-platform searchers (HTTP/gh mocked)
│
├── scripts/
│   ├── lib/tests/
│   │   ├── conftest.py             # sys.path → scripts/
│   │   └── unit/                   # 303 — language_config, model_config, discovery, orchestrator, dedup, hybrid,
│   │                               # model_utils, golden runner, BaseCLIScript (test_base_cli.py)
│   └── cli/tests/
│       ├── conftest.py             # sys.path → scripts/
│       ├── unit/                   # 441 — one file per CLI script, incl. format_code and task_monitor
│       ├── integration_mock/       # 16 — commit quality, KANBAN workflow
│       ├── integration_real/       # 9 — real git operations
│       └── e2e/                    # 25 — commit and KANBAN workflows, delegation workflow
│
└── tests/                          # cross-component: drives several components at once
    ├── conftest.py                 # sys.path → scripts/ (append)
    ├── unit/                       # 12 — configs/delegation-rules.json
    ├── integration_real/           # 11 — AGENT.md files of several agents, Ollama CLI
    └── e2e/                        # 18 — agent and skill workflows through the CLI scripts
```

---

## One Invocation for Every Suite (#21)

Every suite runs from `~/.claude` in one pytest invocation:

```bash
cd ~/.claude
python -m pytest -q -m "not integration_real" \
  --ignore=agents/security-safety-analyzer/tests/integration_mock/test_orchestrate.py \
  --deselect "agents/clean-code-analyzer/tests/e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates"
```

One tier at a time: `python -m pytest -q -m unit` (or `integration_mock`, `integration_real`, `e2e`).
One component: `python -m pytest <component>/tests`, from any directory inside the repo (the root
`pytest.ini` is found upward).

What makes it work, and what keeps it working:
- **Each agent owns one uniquely named package**: `cca/`, `ssa/`, `bba/` under the agent's `scripts/`, and
  `search_tech/` for the skill. Nothing importable is called `common`, `checkers` or `orchestrate` at top level.
  `scripts/orchestrate.py` is a three-line CLI wrapper, never imported by tests.
- **No `__init__.py` in test trees, nor in the agents' `scripts/` dirs.** With `--import-mode=importlib`, pytest
  names a test module after its path from the rootdir, so two `tests/unit/test_cache.py` stay distinct. An
  `__init__.py` makes pytest name it after the package instead (`scripts.tests.conftest`), and two agents collide.
- **Only conftests touch `sys.path`.** A test file that inserts its own path with a hard-coded depth breaks
  the moment it moves; worse, `scripts/lib` on the path makes `lib/cli` shadow `scripts/cli` for every test after it.
- Tests import `from .conftest` nowhere: shared test switches are markers (`@pytest.mark.live_ai`) that a
  conftest turns into skips.
- The AI client holds no cache state: each agent's `model_utils` shim passes its own `CACHE` on every call, so
  loading three agents in one process cannot make one read another's cache.

## conftest.py Pattern

Each `<component>/tests/conftest.py` puts the component's source root on `sys.path`, relative to itself:

```python
# agents/<NAME>/tests/conftest.py, skills/<NAME>/tests/conftest.py
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# scripts/lib/tests/conftest.py, scripts/cli/tests/conftest.py
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # → scripts/

# tests/conftest.py (append, not insert: an agent's scripts dir stays first)
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
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

`tests/fixtures/integration_real/` holds ten minimal projects, one per detected
project type, read by `tests/integration_real/test_universal_detection.py`. Each is
written against the exact regexes its analyzer uses, so a fixture edit is a contract change:

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

`~/.claude/fixtures/` is shared test data, owned by no component, so it stays at the root rather than in one
component's `tests/fixtures/`:

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
- SSA `tests/integration_mock/test_orchestrate.py` — runs a full orchestrate.py against the live AI with no timeout
  (`--ignore` it). Despite the tier name it is not mocked (#36).
- CCA `tests/e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates` — 300s limit; passes in
  ~193s when the GPU is free.

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
