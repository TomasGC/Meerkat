# KANBAN - Meerkat

Track of work sessions and completed tasks linked to GitHub issues.

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
