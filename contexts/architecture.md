# Architecture - Meerkat

**Purpose**: Claude Code optimization framework — delegates mechanical tasks to local tools (Ollama + Python scripts), keeps Claude focused on strategic reasoning.

**Last Updated**: 2026-09-04

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
Ollama  Scripts  Agents
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
│   │   ├── scripts/                 # Analysis scripts + prompts/claude/
│   │   └── tests/                   # Co-located 4-tier tests
│   ├── clean-code-analyzer/         # 12-principle code quality analyzer (SOLID, DRY, KISS, YAGNI, CQRS, DDD, SLAP, LoD, Comments, Naming, ErrorHandling, Composition)
│   │   ├── AGENT.md
│   │   ├── scripts/                 # orchestrate.py + 12 checkers + common/ (ollama_utils, cache, file_utils)
│   │   └── tests/                   # 472 unit + 17 integration/mock (99% coverage)
│   ├── ci-fix-proposer/
│   ├── code-analyzer/
│   ├── ollama-router/
│   ├── task-delegator/
│   ├── task-monitor/
│   ├── test-runner/
│   └── git-helper/
│
├── scripts/                         # Python 3.12+ automation
│   ├── cli/                         # 37 CLI scripts + co-located tests
│   │   ├── agents/ci_fix_proposer/  # + tests/
│   │   ├── agents/code_analyzer/    # + tests/
│   │   └── skills/analyze_commit/   # + tests/
│   ├── common/                      # Shared libraries + co-located tests
│   │   └── cli/                     # + tests/
│   └── tests/                       # Scripts-level tests (e2e, integration-reals)
│
├── skills/                          # User-invocable slash commands
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
| 10-60s | Agents (background) | Test execution, code analysis, test gap detection |
| Strategic | Claude | Architecture, bug root cause, refactoring strategy |

### Ollama Model Tiers

| Tier | Model | RAM | Use case |
|------|-------|-----|---------|
| Hot | qwen2.5-coder:7b, llama3.2:3b | Preloaded | Instant validation |
| Warm | qwen2.5-coder:14b, deepseek-coder-v2:16b | 9-16 GB | Deep review |
| Cold | llama3.3:70b | 42 GB (SWAP) | Critical architecture |
| Semantic | devstral | ~14 GB | Semantic code analysis (CCA default) |

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
