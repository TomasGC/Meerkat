---
description: Meerkat system architecture, directory structure, agents, scripts, and Ollama model tiers
paths: ["**/.claude/**"]
---

# Architecture - Meerkat

**Purpose**: Claude Code optimization framework with task delegation, multi-environment support, and project templating

---

## Overview

Meerkat delegates mechanical tasks to local tools (Ollama MCP + Python scripts) while keeping Claude focused on strategic reasoning.

### Core Principles

1. **Strategic Delegation**: Mechanical tasks → Ollama MCP tools / Python scripts
2. **Hybrid Approach**: Data gathering (scripts) + Analysis (Claude)
3. **Multi-Environment**: Profile-based configuration for different environments
4. **Project Templating**: Language-specific project scaffolding with injection system

---

## Directory Structure

```
~/.claude/
├── CLAUDE.md                        # Global instructions
├── CLAUDE.local.md                  # Personal overrides (gitignored)
├── settings.json                    # Global permissions
├── settings.local.json              # Local account config (gitignored)
├── contexts/                        # On-demand context files (not auto-loaded)
├── agents/                          # Specialized autonomous agents
├── skills/                          # User-invocable commands
├── scripts/                         # Python 3.12+ automation scripts
│   ├── cli/                         # CLI scripts
│   ├── common/                      # Shared libraries
│   └── tests/                       # Test suite (pytest)
├── rules/                           # Auto-loaded coding standards + Meerkat context
└── integrations/                    # Environment profiles
```

---

## Key Components

### Agents
| Agent | Purpose |
|-------|---------|
| `black-box-analyzer` | Universal test gap analysis |
| `ci-fix-proposer` | CI error fix proposals |
| `code-analyzer` | Dead code, DRY violations, complexity |
| `test-runner` | Background test execution |
| `git-helper` | Git analysis |

### Ollama Models
| Mode | Model | Use case |
|------|-------|---------|
| generation | qwen2.5-coder:32b | Code generation, test writing |
| analysis | qwen3:8b | Coverage analysis, reasoning |
| quick | qwen2.5-coder:7b | Build error investigation |

### Ollama Integration
- **Claude Code sessions**: via MCP tools (`ollama_generate`, `ollama_chat`)
- **Unattended scripts**: via `common_config.run_ollama()` subprocess

---

## Testing

**Test suite**: `scripts/tests/` (pytest 3.12+)
**Run**: `python -m pytest scripts/tests/ -v`
**Coverage target**: ≥ 80%
