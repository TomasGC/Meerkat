# Architecture - Meerkat

**Purpose**: Claude Code optimization framework — delegates mechanical tasks to local tools (local AI + Python scripts), keeps Claude focused on strategic reasoning.

**Last Updated**: 2026-09-09

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
│   │   ├── scripts/                 # orchestrate.py + 11 checkers + common/ (model_utils, cache, file_utils)
│   │   └── tests/                   # 465 unit / 17 integration/mock / 16 integration/real / 9 e2e / 73 untiered
│   ├── security-safety-analyzer/    # 10-checker security and safety analyzer (Security, Crypto, Deserialization, Misconfiguration, SensitiveData, CrashBug, Concurrency, ResourceLeak, ErrorHandling, PromptInjection)
│   │   ├── AGENT.md
│   │   └── scripts/                 # orchestrate.py + 10 checkers + common/ (hybrid, dedup, model_utils, cache, file_utils) + prompts/local/
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
│   │   ├── config/                  # model_config — role-based model map
│   │   └── cli/                     # BaseCLIScript + tests/
│   └── tests/                       # Scripts-level tests (e2e, integration-reals)
│
├── skills/                          # User-invocable slash commands
│   └── search-tech/                 # Tech search skill
│       └── scripts/                 # common/ (cache, logger, models, utils) + tests/ (113 tests)
├── rules/                           # Auto-loaded coding standards (14 languages)
├── hooks/                           # Automation hooks
├── integrations/                    # Environment profiles
├── configs/                         # Delegation configuration
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
