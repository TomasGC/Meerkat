# KANBAN - Meerkat

Track of work sessions and completed tasks linked to GitHub issues.

---

2026-10-05 - [#2] Run the test suites on GitHub Actions from any checkout
- Part 1, relocatable checkout: `scripts/lib/paths.py` resolves the repo from `__file__` (`CHECKOUT`); user data (local configs, integration profiles, caches) follows `MEERKAT_HOME`, else the checkout. No code locates the repo through `~/.claude` any more
- One `sys.path` bootstrap per agent package (`cca`, `ssa`, `bba`, `search_tech`) in its `__init__`; 40 per-module blocks and the engine's inserts removed; a guard test fails if a repo package is loaded from outside the checkout
- Every test that reaches the model or the Ollama CLI is marked `live_ai` (#36: SSA's live orchestrate tests left the mock tier, with a 30-minute timeout); `-m "not live_ai"` replaces every `--ignore`/`--deselect` and passes with the model unreachable
- Linux run (python:3.12 container) found two portability bugs, fixed: the golden runner kept `pkg.py` as one file name on POSIX, `open_report.py` crashed without `dotnet`
- Proof: a clone outside `~/.claude` with an empty `HOME`/`USERPROFILE` passes 2587 CI-safe tests; the container passes every tier
- Next: #48 (Condor lint and coverage gates), then the workflows calling Condor's Python and PR pipelines
tags: #ci #paths #testing #portability
Ref: https://github.com/TomasGC/Meerkat/issues/2
Commits: 4ae1a7d, 7d750b9, 19cb2e9

2026-10-04 - [#46] One test layout for every component
- Every agent, skill, `scripts/lib` and `scripts/cli` keeps its tests in `tests/{unit,integration_mock,integration_real,e2e}` with data in `tests/fixtures/`; tests spanning several components moved to a root `tests/`; one `pytest.ini`
- Markers renamed to the directory names (`unit`, `integration_mock`, `integration_real`), applied by one root-conftest rule; 304 explicit tier marks removed
- 186 tests sat in no tier (CCA's root-level files, search-tech's flat suite): a marker-selected CI job would have skipped them; now the four tier runs are disjoint and add up to all 2629
- Only conftests touch `sys.path`: 58 redundant per-file inserts removed, one had put `scripts/lib` on the path and let `lib/cli` shadow `scripts/cli`
- Removed: BBA's second fixture set (read by no test), Pester-era test READMEs; `template-base/` generates the same layout
- Tests: CI-safe run 2531 passed (unchanged), every component green alone, node ids map 1:1 (one rename: `test_base_cli.py`)
tags: #testing #refactor #consistency
Ref: https://github.com/TomasGC/Meerkat/issues/46
Commits: 27a0112, 26a29dd

2026-10-03 - [#22] Reconcile the MetricsCollector API
- Resolved by removal, not reconciliation: of the three `MetricsCollector` copies only search-tech's has a reader (its `--verbose` summary); `lib`'s was write-only (39 `track()` calls in `BaseCLIScript` and 35 CLI scripts, never read) and BBA's had no caller at all
- Deleted `lib`'s collector, every `track()` call, `BaseCLIScript.metrics` and `get_defaults`; deleted BBA's `logger.py` and its 13 tests
- One logging implementation: search-tech imports `ColoredFormatter` and `setup_logger` from `lib.logger` and keeps only its `MetricsCollector`
- 595 lines removed; one-invocation run 2531 passed (2544 minus the 13 deleted tests)
tags: #refactor #logging #yagni
Ref: https://github.com/TomasGC/Meerkat/issues/22
Commit: bf5c22d

2026-10-03 - [#21] Eliminate the duplicated common packages
- One importable package per agent: `cca/`, `ssa/`, `bba/` hold what used to be top-level `common/`, `checkers/` and `orchestrate`; search-tech's `common/` is `search_tech/`; `scripts/orchestrate.py` stays as a CLI wrapper, so every command is unchanged
- `lib.ai.model_utils` no longer enables its cache by importing whichever `common.cache` came first on sys.path: `analyze_*(cache=...)` takes a `ModelCache`, and the BBA and SSA shims pass their own (SSA's hybrid checkers through `run_hybrid(model_cache=)`); CCA stays uncached, as before
- Every suite runs in one pytest invocation from `~/.claude` (2544 CI-safe tests): CCA, SSA and search-tech joined `testpaths`, test-tree `__init__.py` files removed so importlib mode names modules by path, `from .conftest` imports replaced by a `live_ai` marker
- `template-base/common/` renamed `shared/`; obsolete `refactor_imports.py` removed; golden runs bind to the agent package and regenerate byte-identical from any directory
tags: #refactor #packages #testing #cache
Ref: https://github.com/TomasGC/Meerkat/issues/21
Commits: 1bc5b67, 79857ed, 1c72523

2026-10-03 - [#42] Analyze SQL files with dialect-aware SSA and CCA checkers
- SSA security, sensitive_data, misconfiguration, error_handling and concurrency accept the `query` kind, with T-SQL and PostgreSQL rules (dynamic SQL by concatenation, printed secrets, `GRANT ALL` / `TO PUBLIC`, `xp_cmdshell`, empty `CATCH`, `WHEN OTHERS THEN NULL`, `NOLOCK`); every rule has a safe-form negative test (`sp_executesql` with parameters, `format(%I/%L)`, `USING`)
- AI prompts name the detected dialect: `language_config.prompt_language` reads dialect `label`s, `model_utils` fills `{language}` per file (T-SQL / PostgreSQL / SQL), so no checker or prompt changed
- CCA comments (new `--` comment style) and naming (type sizes like `NVARCHAR(255)` exempt) accept SQL; the other 9 stay code-only, each reason recorded next to `CHECKERS`
- A repo with no code is labelled by its other files (`sql`, not `unknown`); new golden `sql_project`: SSA 12, CCA 3, BBA 0 findings
- Tests: scripts 725 → 738, SSA 415 → 455, CCA 540 → 561, BBA 524 → 525; live SSA run on the SQL fixture: pipeline green, model findings noisy
tags: #sql #ssa #cca #languages #golden-tests
Ref: https://github.com/TomasGC/Meerkat/issues/42
Commits: 1fc8bb9, 25c6b2a, b62f7c7, 98c3be0, e5fad1e

2026-10-02 - [#20] Port BBA gap checkers onto the engine, per-language runs
- BBA's 4 gap checkers (never wired since #9) run on `lib.engine.hybrid` through one `run_gap_checker`: mechanical "no test file in this tier" and AI per-function gaps on every run, AI only on untested files; `orchestrate.py --gaps` runs them with the CCA/SSA CLI; golden expected `bba.json` for the 3 projects
- The orchestrator runs each checker once per language group it accepts (`FILE_KINDS`, default code), so no prompt reads "mixed" again; SSA misconfiguration and sensitive_data now scan yaml and Dockerfiles, security Razor views; `.prompt` templates are their own `prompt` kind, scanned by prompt_injection only
- One code-only vote (`dominant_language`) replaces the engine's all-kinds vote, two BBA copies and `find_unused_code`'s; one BBA detector (`detect_project_language`: markers, then the vote) replaces five; `language_for_file`, `is_test_file`, `group_by_language` shared; 4 SSA checkers lost their inline copies
- Reconciliation: line-0 (whole-file) findings never proximity-drop a per-line AI finding; tests are skipped in incremental mode as in full mode
- `python_project` gains a Kubernetes manifest: CCA and BBA goldens unchanged, SSA reports it as yaml; detection before/after on 25 cases, every changed value intended
- Tests: scripts 677 → 725, BBA 503 → 524, SSA 409 → 415, CCA 540; live `--gaps` smoke run on go_project green
tags: #bba #engine #languages #golden-tests #ssa
Ref: https://github.com/TomasGC/Meerkat/issues/20
Commits: 4cc2036, 6b591d5, f2bfd20, 62d45f4, bc10c10, 7917f2d, 4898228, bd266ef

2026-10-02 - [#29] Fold BBA's LANGUAGE_INDICATORS into the shared language config
- `configs/template_languages_config.json` gains a top-level, ordered `project_indicators` list; `language_config.project_indicators()` returns it as an ordered `{language: [markers]}` dict, so `LANGUAGE_INDICATORS` keeps its name and shape
- Ordered list rather than a per-language field: the priority differs from the language order (Go before Python, `solidity`/`sql` last), and `solidity` isn't a scanned language
- The three identical detection loops (`analyze_project_structure`, `extract_api_endpoints`, `parse_test_files`) now share `common.utils.detect_language_from_indicators`; it skips config entries BBA has no `Language` for
- Detection unchanged: the 3 detectors return the same language on the 10 detection fixtures + 8 synthetic cases (order-sensitive pairs, glob markers, empty), before and after; BBA detection fixtures 20 green
- Tests: 5 new `language_config`, 5 new BBA helper; BBA 467, scripts 677, CCA 526, SSA 399 green
tags: #bba #config #languages
Ref: https://github.com/TomasGC/Meerkat/issues/29
Commits: d33939b, b1216da

2026-10-02 - [#31] Merge the model config template under the local file
- `scripts/lib/config/model_config.py` replaced the template with the local file instead of merging over it, so a role added to `template_models_config.json` later never reached an older `local_models_config.json`, and a malformed local file silently yielded an empty config
- Ported `_read` / `_merge` / `_load` from `language_config.py`: template as base, local merged over it, recursive on dicts, override wins on scalars and lists
- 4 new unit tests (later template field, local wins, list/scalar override, malformed local → template); the old test asserting malformed → `{}` now asserts the template
- `contexts/design-patterns.md` #10 corrected (module-level `_config`, not a class singleton) and #23 extended to both configs
tag: #config
Ref: https://github.com/TomasGC/Meerkat/issues/31
Commit: 67a720c

2026-10-02 - [#34] Track the local AI prompt templates
- `.gitignore`'s `*local*` rule hid every `prompts/local/` directory: 6 CCA and 7 BBA prompt templates existed only on the machine that wrote them, so on a fresh clone those AI checkers silently found nothing
- `!**/prompts/local/` re-includes them; the 13 templates are committed; personal files (`*.local.md`, `local_*_config.json`, `settings.local.json`) stay ignored
- Fresh-clone check: `main` misses all 6 CCA prompts, the fix branch misses none
- Found along the way: golden tests can't run from a checkout outside `~/.claude` (hardcoded shared-library path), a prerequisite for CI (#2)
- `settings.json`: BOM dropped, qodo plugin rename followed
tag: #gitignore
Ref: https://github.com/TomasGC/Meerkat/issues/34
Commits: 4d7d7fa, d13843c

2026-10-01 - [#19] Port CCA onto the shared analysis engine
- All 11 CCA checkers route through `lib.engine.hybrid.run_hybrid` (new `mechanical_fn`, `format_ai_violation`, optional `prompt`), so mechanical and AI findings are reconciled; `orchestrate.py` is a thin shim, `common/cache.py` and `common/file_utils.py` are gone
- Per-file AI result cache moved into `run_hybrid` (content hash + prompt + role + agents); failed AI calls are never cached; `CCA_CACHE_DIR` overrides the cache dir
- Pre-existing bugs fixed: KISS and YAGNI mechanical findings sat on line 0, `find_unused_code` let json/md/yaml win the language vote, the incremental e2e test asserted nothing; mechanical checkers now honour the incremental file list
- SSA gained Kotlin weak-crypto and empty-catch rules and a Python eval/exec rule
- Shared golden fixtures (`fixtures/projects/` + `fixtures/golden/`): python/go/kotlin projects, expected CCA and SSA findings compared field by field, AI responses replayed at `call_model_async`; CCA drops 2 duplicate AI findings, SSA 14
- rattler-devkit mechanical counts unchanged after the port (DRY 0, Naming 197, Comments 368, LoD 95); CCA 529, SSA 399, scripts/lib 198, scripts/cli 437 tests green
tags: #cca #engine #refactor #golden-tests #ssa
Ref: https://github.com/TomasGC/Meerkat/issues/19
Commits: 89eeb6c, 1757fe8, afe6348, 8de0eba, 8f1efa1

2026-09-18 - [#18] Extract shared analysis engine from SSA

- `scripts/lib/engine/`: six modules pulled out of SSA — `finding.py` (checker-contract TypedDict, `principle` kept as wire name), `cache.py`, `dedup.py`, `discovery.py` (renamed from `file_utils.py`), `hybrid.py`, `orchestrator.py`
- Cache directory, checker registry, `max_workers`, `app_name` and `label_singular` are now caller-supplied parameters — the only substantive differences between the CCA and SSA copies, per issue #18's diff analysis
- SSA keeps thin shims at `agents/security-safety-analyzer/scripts/common/{cache,dedup,file_utils,hybrid}.py`; `orchestrate.py` shrinks to its checker registry plus a five-line call into the engine
- `run_hybrid`'s AI client now comes straight from `lib.ai.model_utils` instead of through the agent-specific shim; `prompts_dir` moves from an import-time constant to a parameter, with SSA's shim injecting its own default
- Two patch-seam relocations found only by running tests, not by reading the issue: `common.file_utils.subprocess.run` needed `subprocess` re-imported in the shim (same stdlib module object, so no test edits); the five driver-based checkers' `common.hybrid.check_server_available`/`analyze_files_parallel` patches moved to `lib.engine.hybrid` across 7 test files, since that's where the real call site now lives
- SSA's 378 CI-safe tests stayed green after every extraction step (cache, dedup, discovery, hybrid, orchestrator) — fidelity proof per the issue, not just a final check
- Live smoke run on a mixed Python/C# fixture against the local devstral model: mechanical (Crypto's MD5 rule) and AI-layer findings (SQL/command injection) both present, no cross-layer duplicates within a checker

tags: #engine #refactor #ssa #shared-library
Ref: https://github.com/TomasGC/Meerkat/issues/18
Commits: 2c9ebef, 87f550d, b89ce4c, d6ff455, 18cdef1

---

2026-09-17 - [#17] Shared language and tooling configuration

- `configs/template_languages_config.json` + `scripts/lib/config/language_config.py`: 20 languages with extensions, skip dirs, kind, standards document, build/test/format commands, sql and vue dialect detection
- Nine hardcoded language tables across CCA, SSA, BBA and `scripts/` replaced by config reads; CCA and BBA now discover the same 18 files over the BBA fixtures (12 and 14 before)
- `has_inheritance` and `kind` declared per language instead of derived by exclusion, so the inheritance scan and library detection stay identical while the visible language set grows
- Local config merges over the template, so a field added to the template later reaches a local file written before it existed
- `check_server_available` probes `/api/tags` on the configured `local.base_url` instead of shelling out to `ollama list`, and defaults to the `analyzer` role the semantic checkers load
- `language_config` covered by 152 unit tests; CCA availability tests rewritten against the HTTP seam

tags: #config #languages #refactor #local-ai
Ref: https://github.com/TomasGC/Meerkat/issues/17
Commits: 4aab9c5, 8e53040, f680b16

---

2026-09-17 - [#25] Universal project type detection

- `detect_project_types` returns every type present instead of stopping at the first API match, unblocking 20 skipped detection tests
- Android click handlers emit UI handler entry points, so a mobile project no longer reports zero entry points
- 10 minimal fixture projects under `tests/integration/real/fixtures/`, one per detected type, each written against the regexes its analyzer already uses
- `find_project_root` stops at the enclosing `.git`, so a manifest-less fixture resolves to itself rather than an unrelated ancestor

tags: #bba #detection #testing
Ref: https://github.com/TomasGC/Meerkat/issues/25
Commits: d1361bd, 7813424, 6573687

---

2026-09-17 - [#16] Restructure scripts into lib and cli

- `scripts/common/` split into `scripts/lib/` (`ai/model_utils`, `config/model_config`, `cli/BaseCLIScript`); name freed so the four agent-local `common/` packages no longer collide with a shared one
- `skills/search-tech`: per-query result cache (atomic temp-file + `os.replace`, 1h TTL, entry stores its own query/filters and is rejected on mismatch)
- Test suite restored to green: `--import-mode=importlib` in root `pytest.ini`, SSA `AGENT.md` frontmatter added (agent had never been registered), `model-router` rename propagated
- CCA e2e no longer needs docker-compose — `local_ai_service` fixture reads `local.base_url` from config, so switching provider is a config edit
- `check_naming` product bug fixed: the bool-naming rule flagged every unprefixed instance method; now an AST return-type check gates it, clearing false positives on ordinary getters
- Multi-agent dedup e2e dropped its cross-sample count ratio (unsound: each run is an independent nondeterministic sample, both bounds observed to fail); merge exactness moved to unit tests with fixed responses

tags: #refactor #scripts-lib #testing #cache #local-ai
Ref: https://github.com/TomasGC/Meerkat/issues/16
Commits: af54702, 6e52c85, 989b49f

---

2026-09-16 - [#24] BBA analysis result cache

- `common/models.py`: `from_dict` on all 9 dataclasses, mirroring each `to_dict`; enums rebuilt from their values so cached payloads deserialize into typed objects
- `common/cache.py`: per-analyzer `AnalysisResult` cache keyed on `(analyzer, language, source+test file hashes)`; `BBA_CACHE_DIR` env override read lazily; `invalidate_all(include_projects=)` recurses into per-project subdirs
- `parallel_analyzer.py`: cache checked per analyzer before submission — hits skip the work, not just the reporting; report gains a `cache` block (enabled/hits/misses)
- Two latent bugs fixed: `orchestrate.py --clear-cache` never cleared the analysis cache, and an unscoped `--clear-cache` targeted the always-empty base directory
- Tests: 3 previously-skipped cache e2e tests un-skipped and rewritten to assert cache counters instead of comparing wall-clock times; `test_no_cache_flag` asserted instead of ending on a comment; 30 new unit tests (14 `from_dict`, 16 result cache)
- Autouse `BBA_CACHE_DIR` fixture stops the subprocess-based e2e tests writing into the real `~/.cache/black-box-analyzer`

tags: #bba #cache #testing
Ref: https://github.com/TomasGC/Meerkat/issues/24
Commits: 6446fa6, f273a82

---

2026-09-09 - [#12] Security Safety Analyzer (SSA) agent

- New agent `agents/security-safety-analyzer/`: 10 checkers (security, crypto, deserialization, misconfiguration, sensitive_data, crash_bugs, concurrency, resource_leaks, error_handling, prompt_injection), each mechanical pattern/AST pass + AI pass
- `common/hybrid.py`: shared mechanical-then-AI driver for pattern-table checkers; `common/dedup.py`: renders mechanical findings into the prompt and drops AI findings within 3 lines of one, so the two layers never report the same defect twice
- `scripts/model_utils.py`: `extra_slots` — per-file prompt format slots, required to pass each file its own known findings
- CCA `error_handling` checker removed (11 principles now): error handling is a safety concern and SSA owns that detection
- Tests: 340 unit / 28 integration/mock / 25 integration/real / 10 e2e; `integration/real/test_prompt_templates.py` renders every prompt with the slots its callers supply, catching templates that raise KeyError and silently yield zero AI findings
- BBA gap audit on SSA closed two real gaps: `common/file_utils.py` had no tests at all, and `--min-severity` / `--top` / `--output` were uncovered at every tier

tags: #ssa #security #hybrid #local-ai #testing
Ref: https://github.com/TomasGC/Meerkat/issues/12
Commits: a35af97, c20fcbf, 9172f2e

---

2026-09-08 - [#9] Rework BBA: async pipeline, orchestrate.py, test gap checkers

- `orchestrate.py`: new entry point with incremental (branch-vs-main) + full mode, `--role`, `--fast`, `--clear-cache`, delegates to `parallel_analyzer.py` via subprocess
- `checkers/` package: 4 test gap checkers (`check_unit_gaps`, `check_integ_mock_gaps`, `check_integ_real_gaps`, `check_e2e_gaps`) sharing the CCA checker contract; `_utils.py` for shared file discovery
- `prompts/local/`: 4 prompt templates for AI-assisted gap detection (force-added past `*local*` gitignore)
- BBA docs (`AGENT.md`, `doc.md`, `examples.md`): all Ollama/model-name references replaced with "local AI"
- BBA test directories aligned to CCA naming: `unit/`, `integration/mock/`, `integration/real/`
- 35 new tests: 28 unit (4×7 per checker + `_utils`), 4 integration/mock (real filesystem layout), 3 e2e (orchestrate.py `--help`/`--clear-cache`/nonexistent path)

tags: #bba #checkers #orchestrate #testing #local-ai
Ref: https://github.com/TomasGC/Meerkat/issues/9
Commits: 8f5a2ce, 0b38efd, a14f52c, 7957fa9

---

2026-09-08 - [#10] Provider-agnostic local AI abstraction

- configs/template_models_config.json + scripts/model_config.py: role-based model map (analyzer/fast/deep/reasoning/guard) for local + online providers; singleton reader; auto-copies template on first run
- scripts/model_utils.py: shared generic local AI client; host/port from config; role-based API (call_model, analyze_files_parallel); no model names in code
- BBA + CCA: common/model_utils.py shims replacing ollama_utils.py; all callers updated to role-based API
- Renamed agents: ollama-router → model-router, start-ollama-mcp → start-model-server; cache functions get_ollama_* → get_model_*
- 54 new unit tests: model_config (12), LocalAIMonitor (10), analyze_files_parallel (4), call_model_async + _parse_local_server (6), CLI role resolution (2), test isolation fixes (20)
tags: #config #refactor #provider-agnostic #local-ai #testing
Ref: https://github.com/TomasGC/Meerkat/issues/10
Commits: 63c01f1, 48a0f90, 14505bb

---

2026-09-04 - [#7] Rework context skills to use contexts/ directory layout
- load_session_context.py, update_kanban.py, search_kanban.py: all default paths updated to .claude/contexts/kanban.md
- update-context skill: file references updated; File Location constraint block added; contexts/ sub-files (tests.md, conventions.md, commands.md) now known
- project-setup skill: CREATE generates contexts/ layout; UPDATE detects old flat layout and offers migration
tags: #skills #contexts #refactor
Ref: https://github.com/TomasGC/Meerkat/issues/7
Commit: 5030654

---

2026-09-04 - [#4] Clean Code Analyzer (CCA) Agent
- Added CCA agent: 12 principle checkers (SOLID, DRY, KISS, YAGNI, CQRS, DDD, SLAP, LoD, Comments, Naming, ErrorHandling, Composition) running in parallel via ThreadPoolExecutor
- Async pipeline: asyncio.run() with all HTTP requests in-flight simultaneously; line-aligned chunking for large files; per-file Ollama result cache with TTL
- Branch-vs-main default mode (incremental by default); --full/--fast/--model flags; devstral as default semantic model (replaces qwen3:8b/qwen2.5-coder:7b)
- Validated on rattler-devkit: 314 files, 1025 violations detected; DRY + Composition clean; zero timeouts
- 472 unit tests + 17 integration/mock tests — 99% coverage; structural prompt tests for all 12 prompt templates
- Golden-path prompt tests (needs Ollama) tracked in issue #5
tags: #cca #ollama #async #testing #devstral #clean-code
Ref: https://github.com/TomasGC/Meerkat/issues/4
Commits: 0e12661, d495fe2, 56f49f0, 43c8676, edb7793

---

2026-07-09 - [#3] Black-Box Analyzer — Script Improvements & Test Coverage
- Expanded BBA test coverage: diff_analysis, common/utils, common/cache, common/logger, coverage pipeline
- Replaced always-skip Ollama stubs with live integration-reals tests
- Extracted Ollama prompt strings into .prompt files (prompts/claude/)
- Added typed-agents mode: 4 parallel Ollama agents (unit/int_mock/int_real/e2e), merging deduplicated results
- library_analyzer: phases 1+4b now run concurrently; scan_tdd_refactoring: --agents N parallel runs
- prioritize_by_risk: library scenario risk scoring across business/technical/failure axes
- Analyzers: consistent Ollama prompt integration across api/cli/mobile/frontend/desktop/blockchain/event-driven
- Added doc.md (phase reference) and examples.md
tags: #bba #testing #ollama #parallel
Ref: https://github.com/TomasGC/Meerkat/issues/3
Commit: 119bbaa

---

2026-07-09 - [#1] Meerkat — Initial Setup
- Initialized repository with base Claude Code configuration and global instructions
- Added coding standards rules for 14 languages/frameworks
- Added multi-environment integration profiles (GitHub public + private local)
- Added automation hooks (session-start, delegation-router, pre-commit-validation)
- Added Python automation script library (37 scripts: git, code analysis, KANBAN, validation)
- Added universal black-box test analyzer agent (19+ project types, risk-based prioritization)
- Added delegation agents: task-delegator, ci-fix-proposer, code-analyzer, ollama-router, test-runner, git-helper, task-monitor
- Added 13 skills, docs/, template-base/ (9-language project templates + inject.py)
- Added 4-tier co-located test structure (pytest.ini, conftest.py, scripts/cli/tests/, etc.)
- Reworked contexts: architecture, commands, conventions, tests; removed delegation-strategy
tags: #setup #agents #scripts #hooks #integrations #skills #docs #testing
Ref: https://github.com/TomasGC/Meerkat/issues/1
Commits: aa582e9, eef247e, b16b1c3, 9e7ccab, e49eda1, d52d1d3, b6a4ea8, e46c3fa, f672bcf, cf704eb

---

## Notes

- **One entry per issue** - Updated each time you work on it (not one entry per session)
- **Date** - Last update date
- **Title line**: `YYYY-MM-DD - [#ID] Title`
- **Description** - Bullet points describing work done (max 6 lines)
- **Tag/Tags** - Topic tags with # prefix (singular if 1, plural if multiple)
- **Ref/Refs** - GitHub issue link (singular if 1, plural if multiple)
- **Commit/Commits** - Commit hashes (singular if 1, plural if multiple)
- **Language**: English only
- **Updated by**: `/update-context` skill automatically
- **All tasks tracked in GitHub Issues** - This file is just a log
