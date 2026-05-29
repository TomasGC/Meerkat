# Architecture - Meerkat

**Purpose**: Claude Code optimization framework with task delegation, multi-environment support, and project templating

**Last Updated**: 2026-05-29

---

## Overview

Meerkat is a Claude Code configuration framework that delegates mechanical tasks to local tools (Ollama + Python scripts) while keeping Claude focused on strategic reasoning. It provides multi-environment integration profiles, a universal project template system, and a library of specialized agents and skills.

### Core Principles

1. **Strategic Delegation**: Mechanical tasks → Local tools (0 Claude tokens)
2. **Hybrid Approach**: Data gathering (scripts) + Analysis (Claude)
3. **Multi-Environment**: Profile-based configuration for different environments
4. **Project Templating**: Language-specific project scaffolding with injection system

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Claude (Orchestrator)                     │
│                Strategic Reasoning & Decisions                │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                     Delegation Router                         │
│         (Analyzes task → Routes to appropriate tool)          │
└──────────────────────────────────────────────────────────────┘
                             │
       ┌─────────────────────┼──────────────────────┐
       ▼                     ▼                      ▼
┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
│Ollama Models│   │ Python Scripts   │   │ Claude Agents    │
│ (qwen:7b)   │   │ (AST, Regex)     │   │ (Specialized)    │
└─────────────┘   └──────────────────┘   └──────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   Integration Profiles                        │
│        (VCS, CI, Docs, Issues - Multi-environment)            │
└──────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
~/.claude/
├── CLAUDE.md                        # Global instructions
├── CLAUDE.local.md                  # Personal overrides (gitignored)
├── README.md                        # Project overview
├── settings.json                    # Global permissions
├── settings.local.json              # Local account config (gitignored)
│
├── contexts/                        # Auto-loaded context files
│   ├── architecture.md              # This file
│   ├── kanban.md                    # Work history
│   ├── commands.md                  # Global script commands
│   ├── conventions.md               # Commit format, structure rules
│   └── delegation-strategy.md       # Delegation patterns
│
├── agents/                          # Specialized autonomous agents
│   ├── black-box-analyzer/          # Universal test gap analyzer
│   ├── ci-fix-proposer/             # CI error fix proposals
│   ├── code-analyzer/               # Mechanical code pattern detection
│   ├── code-reviewer/               # Code review agent
│   ├── git-helper/                  # Git operations
│   ├── ollama-router/               # Ollama model routing
│   ├── task-delegator/              # Task routing orchestrator
│   ├── task-monitor/                # Background task monitoring
│   └── test-runner/                 # Test execution agent
│
├── skills/                          # User-invocable commands
│   ├── analyze-code/                # Code quality analysis
│   ├── analyze-commit/              # Pre-commit validation
│   ├── analyze-feature/             # Feature analysis
│   ├── analyze-github-ci/           # CI failure analysis
│   ├── analyze-tests/               # Test coverage analysis
│   ├── agent-setup/                 # Create/update agents
│   ├── create-project-template/     # Create project templates
│   ├── index-documentation/         # Documentation indexing
│   ├── project-setup/               # Initialize/update .claude/
│   ├── script-setup/                # Create/update scripts
│   ├── search-tech/                 # Technical search
│   ├── skill-setup/                 # Create/update skills
│   ├── start-session/               # Session startup
│   └── update-context/              # Update project documentation
│
├── scripts/                         # Python 3.12+ automation scripts
│   ├── cli/                         # CLI scripts (37 scripts)
│   ├── common/                      # Shared libraries
│   ├── delegators/                  # Data gathering scripts
│   ├── benchmarks/                  # Ollama latency benchmarks
│   ├── tests/                       # Test suite (pytest)
│   └── requirements.txt
│
├── rules/                           # Auto-loaded coding standards
│   └── standards-*.md               # 14 language/framework standards
│
├── integrations/                    # Environment profiles
│   ├── default.json                 # GitHub (public)
│   └── *.local.json                 # Private configs (gitignored)
│
├── hooks/                           # Automation hooks
│   ├── delegation-router.sh
│   ├── pre-commit-validation.sh
│   └── session-start.sh
│
├── configs/                         # Delegation configuration
│   ├── delegation-rules.json
│   └── hooks.json
│
├── docs/                            # User documentation
│   ├── delegation.md
│   ├── file-structure.md
│   ├── integrations.md
│   ├── scripts.md
│   └── settings.md
│
└── template-base/                   # Project template system (gitignored)
    ├── inject.py                    # Template injection (3 subcommands)
    ├── templates/                   # Base templates
    ├── content/                     # Language-specific content (9 langs)
    └── common/                      # Files copied to all projects
```

---

## Key Components

### 1. Agents

| Agent | Purpose | Delegates to |
|-------|---------|-------------|
| `black-box-analyzer` | Universal test gap analysis (15+ project types) | Python scripts + AST |
| `ci-fix-proposer` | CI error fix proposals | `propose_ci_fixes.py` + Ollama |
| `code-analyzer` | Dead code, DRY violations, complexity | `find_unused_code.py`, `find_duplicates.py`, `calculate_complexity.py` |
| `ollama-router` | Routes tasks to appropriate Ollama model | Ollama (3 tiers: hot/warm/cold) |
| `task-delegator` | Orchestrates mechanical task routing | Scripts + Ollama + Agents |
| `test-runner` | Background test execution | pytest / go test / dotnet test |
| `git-helper` | Git analysis without consuming tokens | git CLI |
| `task-monitor` | Background task monitoring | Bash + Ollama |

### 2. Scripts (scripts/cli/)

**Git & Project**:
- `extract_issue.py` — Extract GitHub issue from branch/commit
- `format_commit_message.py` — Validate/format commit messages
- `check_git_repo.py` — Verify git repo state
- `get_branch_summary.py`, `get_commit_info.py`

**Code Analysis**:
- `analyze_commit_quality.py` — ORCA/OWASP/SonarQube patterns
- `analyze_code_patterns.py` — Orchestrator for code analysis
- `find_unused_code.py` — AST dead code detection
- `find_duplicates.py` — DRY violation detection
- `calculate_complexity.py` — Cyclomatic complexity

**KANBAN & Context**:
- `search_kanban.py`, `update_kanban.py`
- `generate_kanban_entry.py`, `generate_comment.py`
- `load_session_context.py`

**Validation**:
- `validate_markdown.py`, `validate_skill_structure.py`
- `validate_cross_platform.py`, `run_all_validations.py`
- `analyze_work_patterns.py`

### 3. Integration Profiles

Profile-based configuration for VCS, CI, docs, and issue tracking:

```json
{
  "vcs": { "provider": "github", "url": "...", "api_url": "..." },
  "ci": { "provider": "github-actions" },
  "docs": { "provider": "github-pages", "url": "..." },
  "issues": { "provider": "github", "issue_format": "#(\\d+)" }
}
```

Switch profiles: `python scripts/cli/switch-profile.py --list`

### 4. Template System (template-base/)

Generates project `.claude/` structure via `inject.py`:

```bash
# 3 subcommands:
inject.py template  <template> <output> <lang>   # Injects {{PLACEHOLDERS}}
inject.py conventions <output> <lang>             # base + lang + Python (always)
inject.py commands    <output> <lang>             # header + lang-specific commands
```

**9 supported languages**: go, node, vuejs, dotnet, cshtml, kotlin, python, bash, powershell

---

## Delegation Strategy

### Mechanical → Local Tools

| Latency | Tool | Tasks |
|---------|------|-------|
| <1s | Python scripts | Formatting, git ops, commit checks |
| 2-10s | Ollama (hot tier) | Syntax validation, quick reviews |
| 10-60s | Agents (background) | Test execution, code analysis, test gap detection |

### Strategic → Claude

Architecture decisions, bug root cause analysis, refactoring strategy, code explanations, context synthesis.

---

## Ollama Model Tiers

| Tier | Models | RAM | Use case |
|------|--------|-----|---------|
| Hot | qwen2.5-coder:7b, llama3.2:3b, llama-guard3:1b | Preloaded | Instant validation, quick review |
| Warm | qwen2.5-coder:14b, deepseek-coder-v2:16b | ~9-16GB | Deep review, debugging |
| Cold | llama3.3:70b | 42GB (SWAP) | Critical architecture decisions |

---

## Testing

**Test suite**: `scripts/tests/` (pytest 3.12+)
**Run**: `python -m pytest scripts/tests/ -v`
**Coverage target**: ≥ 80%
