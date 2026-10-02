# Architecture - Meerkat

**Purpose**: AI coding assistant optimization framework (Claude Code today) — delegates mechanical tasks to local tools (local AI + Python scripts), keeps the assistant focused on strategic reasoning. Name and vision: see the GitHub wiki.

**Direction**: support for other assistants (Codex, others) is planned. Keep the assistant-agnostic core (`scripts/lib/`) separate from the Claude Code host layer (`CLAUDE.md`, skills, hooks, `AGENT.md`, `settings.json`); name the role ("the coding assistant"), not the product, in docs and new designs.

**Last Updated**: 2026-10-01

---

## Core Principles

1. **Strategic Delegation**: Mechanical tasks → Local tools (0 Claude tokens)
2. **Hybrid Approach**: Data gathering (scripts) + Strategic analysis (orchestrator)
3. **Multi-Environment**: Profile-based config for different VCS/CI providers
4. **Co-located Tests**: 4-tier test pyramid next to source (units/integration-mocks/integration-reals/e2e)

---

## System Architecture

```
Orchestrator (strategic reasoning)
         │
         ▼
Delegation Router (task type → tool)
         │
   ┌─────┼──────┐
   ▼     ▼      ▼
Local AI  Scripts  Agents
 (LLM)  (AST/Regex) (autonomous)
```

---

## Directory Structure

```
~/.claude/
├── CLAUDE.md / CLAUDE.local.md      # Global + personal instructions
├── settings.json / settings.local.json
│
├── contexts/                        # Auto-loaded session context
│   ├── kanban.md                    # Work history
│   ├── architecture.md              # This file
│   ├── commands.md                  # Script commands reference
│   ├── conventions.md               # Commit format, naming
│   └── tests.md                     # 4-tier test structure
│
├── agents/                          # Autonomous agents
│   ├── black-box-analyzer/          # Universal test gap analyzer (19+ project types)
│   │   ├── AGENT.md
│   │   ├── scripts/                 # orchestrate.py + parallel_analyzer + checkers/ (4 gap) + prompts/local/
│   │   └── tests/                   # 415 unit / 47 integration/mock / 30 integration/real (incl. 10 detection fixtures) / 36 e2e
│   ├── clean-code-analyzer/         # 11-principle code quality analyzer (SOLID, DRY, KISS, YAGNI, CQRS, DDD, SLAP, LoD, Comments, Naming, Composition)
│   │   ├── AGENT.md
│   │   ├── scripts/                 # orchestrate.py (registry + call into lib.engine.orchestrator) + 11 checkers
│   │   │                            # (all via lib.engine.hybrid.run_hybrid) + common/model_utils shim + prompts/local/
│   │   └── scripts/tests/           # unit + integration/mock (526) / integration/real (live AI) / e2e (15)
│   ├── security-safety-analyzer/    # 10-checker security and safety analyzer (Security, Crypto, Deserialization, Misconfiguration, SensitiveData, CrashBug, Concurrency, ResourceLeak, ErrorHandling, PromptInjection)
│   │   ├── AGENT.md
│   │   └── scripts/                 # orchestrate.py (registry + call into lib.engine.orchestrator) + 10 checkers
│   │       │                        # + common/ (thin shims over lib.engine: hybrid, dedup, cache, file_utils; model_utils shims lib.ai) + prompts/local/
│   │       └── tests/               # 340 unit / 28 integration/mock / 25 integration/real / 10 e2e
│   ├── ci-fix-proposer/
│   ├── code-analyzer/
│   ├── model-router/
│   ├── task-delegator/
│   ├── task-monitor/
│   ├── test-runner/
│   └── git-helper/
│
├── scripts/                         # Python 3.12+ automation
│   ├── cli/                         # 37 CLI scripts + co-located tests
│   │   ├── tests/                   # units/ + integration-mocks/ + integration-reals/
│   │   ├── agents/task_monitor/     # + tests/units/
│   │   └── utils/switch_profile.py
│   ├── lib/                         # Shared library — importable by scripts, skills, plugins, agents
│   │   ├── ai/                      # model_utils — local AI client
│   │   ├── config/                  # model_config (roles) + language_config (languages, skip dirs, standards)
│   │   ├── engine/                  # shared analysis engine (extracted from SSA, issue #18): finding, cache,
│   │   │                            # dedup, discovery, hybrid, orchestrator — cache dir/registry/max_workers/labels
│   │   │                            # are caller-supplied params, no agent name hardcoded; used by SSA and CCA (#19)
│   │   ├── testing/                 # golden.py — golden fixture runner: replay recorded AI responses, compare expected
│   │   └── cli/                     # BaseCLIScript + tests/
│   └── tests/                       # Scripts-level tests (e2e, integration-reals)
│
├── fixtures/                        # Shared test data, usable by every agent and skill
│   ├── projects/                    # python_project, go_project, kotlin_project — source only, seeded issues
│   └── golden/<project>/            # expected/<agent>.json + ai_responses/<agent>/<prompt>.json
│
├── skills/                          # User-invocable slash commands
│   └── search-tech/                 # Tech search skill
│       └── scripts/                 # common/ (cache, logger, models, utils) + tests/ (113 tests)
├── rules/                           # Auto-loaded coding standards (14 languages)
├── hooks/                           # Automation hooks
├── integrations/                    # Environment profiles
├── configs/                         # template_ + local_ config pairs: models, languages, delegation
└── docs/                            # User documentation
```

---

## Delegation Matrix

| Latency | Tool | Tasks |
|---------|------|-------|
| <1s | Python scripts | Formatting, git ops, commit checks |
| 2-10s | Ollama hot tier | Syntax validation, quick review |
| 10-60s | Agents (background) | Test execution, code analysis, test gap detection, security and safety analysis |
| Strategic | Claude | Architecture, bug root cause, refactoring strategy |

### Local AI Model Tiers

| Tier | Model | RAM | Use case |
|------|-------|-----|---------|
| Hot | qwen2.5-coder:7b, llama3.2:3b | Preloaded | Instant validation |
| Warm | qwen2.5-coder:14b, deepseek-coder-v2:16b | 9-16 GB | Deep review |
| Cold | llama3.3:70b | 42 GB (SWAP) | Critical architecture |
| Semantic | devstral-small-2 | ~14 GB | Semantic code analysis (CCA default) |

---

## Shared Language Configuration

One declarative table, `configs/template_languages_config.json`, is the only place
language knowledge lives. `scripts/lib/config/language_config.py` is its singleton
reader; `local_languages_config.json` is auto-copied on first import and merges over
the template, so a field added to the template later still reaches an older local file.

Per language: extensions, skip directories, `kind` (code / markup / data / query /
config), `has_inheritance`, comment style, filename pattern, the matching
`rules/standards-*.md`, and build / test / format commands. `sql` and `vue` carry
dialect blocks, resolved from file content where the extension is ambiguous.

Separately, a top-level `project_indicators` list types a whole project from its
marker files (`go.mod`, `*.csproj`, …), first match wins (#29). It is an ordered
list, not a per-language field, because its priority differs from the language
order (Go before Python, content-only `solidity`/`sql` last) and it can name
languages that aren't scanned for files (`solidity`).

CCA, SSA and BBA all discover files from this one table, so they can no longer
disagree about which files exist.

---

## Integration Profiles

Profile-based config for VCS, CI, docs, issues:

```json
{
  "vcs": { "provider": "github", "url": "...", "api_url": "..." },
  "ci": { "provider": "github-actions" },
  "issues": { "provider": "github", "issue_format": "#(\\d+)" }
}
```

Switch: `python scripts/cli/switch-profile.py --list`
