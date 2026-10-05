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
│       ├── integration_mock/       # 32 — real filesystem, AI mocked at two seams; test_golden_projects.py
│       ├── integration_real/       # 29 — prompt slot rendering (no server) + live AI per checker, test_orchestrate_live.py
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

Every suite runs from the checkout root in one pytest invocation, any checkout (#2):

```bash
python -m pytest -q -m "not live_ai"
```

One tier at a time: `python -m pytest -q -m "unit and not live_ai"` (or `integration_mock`, `integration_real`, `e2e`): what CI runs.
The live-AI tier: `python -m pytest -q -m live_ai`.
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
- **Every test that reaches the model server or the Ollama CLI carries `live_ai`**, whatever its tier, so
  `-m "not live_ai"` never calls the model. Proof (#2): every tier passes with `local.base_url` pointed at an
  unreachable port through `MEERKAT_HOME`. A new AI-calling test without the marker breaks CI on a runner
  with no server, which is the point.
- The AI client holds no cache state: each agent's `model_utils` shim passes its own `CACHE` on every call, so
  loading three agents in one process cannot make one read another's cache.

## conftest.py Pattern

Each `<component>/tests/conftest.py` puts the component's source root on `sys.path`, relative to itself:

```python
# agents/<NAME>/tests/conftest.py, skills/<NAME>/tests/conftest.py
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))  # this checkout's shared library
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

## Slow Live-AI Tests

With the local model mostly offloaded to CPU, two `live_ai` tests run long; both are bounded, so a slow model fails
them instead of hanging the session:
- SSA `tests/integration_real/test_orchestrate_live.py` — full orchestrate.py runs, 30 minutes each. It sat in the
  mock tier with no timeout until #36.
- CCA `tests/e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates` — 300s limit; passes in
  ~193s when the GPU is free.

## Clones and Worktrees Are Faithful (#2)

Nothing locates the repository through `~/.claude` any more. `scripts/lib/paths.py` resolves it from its own file:
- `CHECKOUT` — code, config templates, fixtures: always the checkout the code was imported from.
- `user_root()` — the user's data: `configs/local_*_config.json`, `integrations/`, the CCA and SSA caches. It is
  `CHECKOUT` unless `MEERKAT_HOME` points elsewhere, read on every call.

Each agent package (`cca`, `ssa`, `bba`, `search_tech`) puts this checkout's `scripts/` on `sys.path` once, in its
`__init__`, derived from `__file__`; entry scripts that import `lib` before any package do the same in one line.
So a worktree, a clone or a CI runner tests its own code, and `test_paths.py` fails if any module of the repo's
own packages (`lib`, `cli`, `cca`, `ssa`, `bba`, `search_tech`) is loaded from outside the checkout.

Proof (#2): a clone in `C:\dev\tmp`, with `HOME` and `USERPROFILE` pointed at an empty directory (on Windows
`Path.home()` reads `USERPROFILE`), passes the CI-safe run; local configs are created in the clone and the
`~/.claude` worktree is untouched. A `python:3.12` container passes the four tiers from a fresh clone.

Still host paths, on purpose: `~/.claude/logs/delegation-stats.jsonl` (written by the `hooks.json` hook) and
`~/.cache/*` (search-tech, BBA). Inside `lib/`, modules reached from `lib/__init__` import `paths` relatively:
pytest's importlib mode loads `scripts/lib` as `scripts.lib` before any conftest has put `scripts/` on the path.

## Prompt Templates Are Tracked

`.gitignore`'s `*local*` rule (personal files) would also hide `agents/*/scripts/prompts/local/`, the local-AI
prompt templates; `!**/prompts/local/` re-includes them (#34). A new prompt file there is tracked like any source
file — no `git add -f` needed.
