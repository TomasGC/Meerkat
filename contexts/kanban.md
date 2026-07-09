# KANBAN - Meerkat

Track of work sessions and completed tasks.

---

2026-07-09 - [#3] Black-Box Analyzer — Test Suite & Script Improvements
- Reorganized test suite into 4-tier co-located structure (units/integration-mocks/integration-reals/e2e) per source
- Added root pytest.ini with markers + conftest.py auto-marking by directory name
- Expanded BBA test coverage: diff_analysis, common/utils, common/cache, common/logger, coverage pipeline
- Replaced always-skip Ollama stubs with live integration-reals tests
- Extracted Ollama prompt strings into .prompt files (prompts/claude/)
- Added typed-agents mode: 4 parallel Ollama agents (unit/int_mock/int_real/e2e), merging deduplicated results
- library_analyzer: phases 1+4b now run concurrently; scan_tdd_refactoring: --agents N parallel runs
- prioritize_by_risk: library scenario risk scoring across business/technical/failure axes
- Analyzers: consistent Ollama prompt integration across api/cli/mobile/frontend/desktop/blockchain/event-driven
tags: #testing #bba #refactoring #4-tier #ollama #parallel
Commits: f2092bf, 36640b3, 911ae6a, fe1e199, 4130cad, a054c99, 63bd4d6, b7f617b

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
Commits: aa582e9, eef247e, b16b1c3, 9e7ccab, e49eda1, d52d1d3, b6a4ea8, e46c3fa, f672bcf, cf704eb

---

## Notes

- **One entry per issue** - Updated each time you work on it (cumulative, not per session)
- **Date** - Last update date
- **Format**: `YYYY-MM-DD - [#ID] Title`
- **Language**: English only
