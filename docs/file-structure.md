# File Structure Guide

> **TL;DR**: Complete reference for `~/.claude/` organization - what each file/folder does, which are committed vs gitignored, and how they work together.

---

## Quick Navigation

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  What You Need                Where to Look                     │
│  ──────────────────────────────────────────────────────────     │
│  Configuration overview    →  ## Root Configuration             │
│  Context files             →  ## Contexts (Auto-loaded)         │
│  User documentation        →  ## Documentation (User Guides)    │
│  Scripts reference         →  ## Scripts (Automation)           │
│  Agents workflows          →  ## Agents (Autonomous)            │
│  Integration profiles      →  ## Integrations (Multi-account)   │
│  Coding standards          →  ## Rules (Standards)              │
│  Skills reference          →  ## Skills (User-invocable)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Tree Overview

```
~/.claude/
│
├── README.md ✅                      # This file (navigation index)
│
├── Root Configuration ✅/❌
├── CLAUDE.md ✅                      # Team instructions (committed)
├── CLAUDE.local.md ❌                # Your preferences (gitignored)
├── settings.json ✅                  # Team settings (committed)
├── settings.local.json ❌            # Your overrides (gitignored)
│
├── contexts/ ✅                      # Auto-loaded context
│   ├── kanban.md ✅                  # Work history
│   ├── kanban.local.md ❌            # Personal notes (gitignored)
│   ├── architecture.md ✅            # System architecture
│   ├── architecture.local.md ❌      # Personal arch notes (gitignored)
│   ├── commands.md ✅                # Script commands reference
│   ├── conventions.md ✅             # File structure & principles
│   ├── conventions.local.md ❌       # Personal commit standards
│   └── delegation-strategy.md ✅     # Token optimization rules
│
├── docs/ ✅                          # User documentation
│   ├── settings.md ✅                # Models, AWS, plugins guide
│   ├── claude-instructions.md ✅     # Language, tone, shortcuts
│   ├── integrations.md ✅            # Multi-account profiles
│   ├── delegation.md ✅              # Delegation architecture
│   ├── scripts.md ✅                 # Python scripts guide
│   └── file-structure.md ✅          # This file
│
├── scripts/ ✅                       # Automation scripts
│   ├── cli/ ✅                       # User-facing scripts
│   │   ├── switch-profile.py ✅      # Integration profile switcher
│   │   ├── extract_issue.py ✅       # Issue ID extraction
│   │   ├── format_commit_message.py ✅ # Commit message formatter
│   │   ├── search_kanban.py ✅       # KANBAN search
│   │   ├── update_kanban.py ✅       # KANBAN updater
│   │   └── analyze_commit_quality.py ✅ # Security/quality checks
│   │
│   ├── common/ ✅                    # Shared utilities
│   │   ├── __init__.py ✅
│   │   ├── integrations.py ✅        # Profile loading
│   │   ├── models.py ✅              # Data models
│   │   ├── utils.py ✅               # Utilities
│   │   └── constants.py ✅           # Constants
│   │
│   ├── tests/ ✅                     # Test suite
│   │   ├── test_integrations.py ✅
│   │   ├── test_extract_issue.py ✅
│   │   ├── fixtures/ ✅              # Test data
│   │   └── ...
│   │
│   └── requirements.txt ✅           # Python dependencies
│
├── agents/ ✅                        # Autonomous workflows
│   ├── ci-fix-proposer/ ✅
│   │   ├── AGENT.md ✅               # Agent definition
│   │   ├── scripts/ ✅               # Agent scripts
│   │   └── tests/ ✅                 # Agent tests
│   │
│   ├── code-analyzer/ ✅
│   ├── black-box-analyzer/ ✅
│   └── test-runner/ ✅
│
├── integrations/ ✅/❌               # Multi-account profiles
│   ├── .active ❌                    # Current profile (gitignored)
│   ├── .gitignore ✅                 # Ignores *.local.json
│   ├── default.json ✅               # GitHub default (committed)
│   ├── work.local.json ❌            # Work profile (gitignored)
│   ├── personal.local.json ❌        # Personal profile (gitignored)
│   └── path-mappings.local.json ❌   # Auto-switch rules (gitignored)
│
├── rules/ ✅                         # Coding standards
│   ├── standards-code-quality.md ✅  # DRY, SOLID, KISS, YAGNI
│   ├── standards-security.md ✅      # Security best practices
│   ├── standards-testing.md ✅       # TDD, coverage requirements
│   ├── standards-typescript.md ✅
│   ├── standards-javascript.md ✅
│   ├── standards-vuejs3.md ✅
│   ├── standards-cshtml.md ✅
│   ├── standards-bash.md ✅
│   ├── standards-powershell.md ✅
│   ├── standards-docker.md ✅
│   ├── standards-kubernetes.md ✅
│   ├── standards-terraform.md ✅
│   ├── standards-postgresql.md ✅
│   ├── standards-sqlserver.md ✅
│   └── standards-kendo.md ✅
│
├── skills/ ✅                        # User-invocable commands
│   ├── analyze-github-ci/ ✅         # Trigger ci-fix-proposer
│   ├── analyze-code/ ✅              # Trigger code-analyzer
│   ├── analyze-tests/ ✅             # Trigger black-box-analyzer
│   ├── analyze-commit/ ✅            # Run commit quality script
│   └── update-context/ ✅            # Update KANBAN/ARCHITECTURE
│
└── .gitignore ✅                     # Git exclusions

✅ = Committed (team)
❌ = Gitignored (personal)
```

---

## Root Configuration

### CLAUDE.md ✅ (Committed)

**Purpose**: Team-wide instructions for how Claude behaves

**Contains**:
- File modification workflow (show diff → wait approval)
- Testing requirements (ALL tests must pass)
- Version control rules (commit format, branch naming)
- Documentation rules (public vs private files)
- Decision-making guidelines (analyze proposals, state reasoning)
- Project architecture principles (TDD, Clean Architecture)

**Who uses**: Entire team (shared standards)

**See also**: [claude-instructions.md](claude-instructions.md)

---

### CLAUDE.local.md ❌ (Gitignored)

**Purpose**: Your personal overrides and preferences

**Contains**:
- Conversation language (French, Spanish, etc.)
- Personal commit message standards
- Personal shortcuts and workflows
- References to other .local.md files

**Who uses**: You only (personal config)

**Pattern**: References other `*.local.md` files via `@contexts/*.local.md`

**See also**: [claude-instructions.md](claude-instructions.md)

---

### settings.json ✅ (Committed)

**Purpose**: Team-wide tool and model configuration

**Contains**:
- Default model (haiku/sonnet/opus)
- Plugin list
- Tool permissions (allow/ask/deny)
- Hook configurations

**Who uses**: Entire team (shared defaults)

**See also**: [settings.md](settings.md)

---

### settings.local.json ❌ (Gitignored)

**Purpose**: Your personal tool and model overrides

**Contains**:
- Personal model preference (e.g., opus)
- AWS profile configuration
- Personal plugin list
- Environment variables (AWS_PROFILE, AWS_REGION)

**Who uses**: You only (personal config)

**See also**: [settings.md](settings.md)

---

## Contexts (Auto-loaded)

**Location**: `contexts/*.md`

**Purpose**: Project knowledge automatically loaded by Claude Code at session start

**Pattern**: Public (committed) + Private (*.local.md, gitignored)

---

### kanban.md ✅ (Committed)

**Purpose**: Work history tracking for team

**Format**:
```markdown
YYYY-MM-DD - [#ISSUE-ID] Title
- Description line 1
- Description line 2
- ...
tags: #tag1 #tag2
Commit: abc123f
```

**Updated by**: `/update-context` skill

**See also**: [scripts.md](scripts.md) - `update_kanban.py`

---

### kanban.local.md ❌ (Gitignored)

**Purpose**: Personal work notes, not shared

**Example**:
```markdown
2026-05-12 - Personal todo
- Fix local issue X
- Test feature Y
```

---

### architecture.md ✅ (Committed)

**Purpose**: System architecture documentation (Meerkat delegation system)

**Contains**:
- Components (agents, scripts, integration profiles)
- Workflows (CI resolution, code analysis, test analysis)
- Performance characteristics
- Extensibility points

**See also**: [delegation.md](delegation.md)

---

### architecture.local.md ❌ (Gitignored)

**Purpose**: Personal architecture notes/experiments

**Example**: Local design decisions, prototype notes

---

### commands.md ✅ (Committed)

**Purpose**: Script commands reference

**Contains**:
- Python script test commands (`cd ~/.claude/scripts && python -m pytest tests/ -v`)
- Script validation commands
- No npm/js/cs/sh/ps1 references (Python + Markdown only)

**See also**: [scripts.md](scripts.md)

---

### conventions.md ✅ (Committed)

**Purpose**: File organization structure and architecture principles

**Contains**:
- .claude/ directory structure
- Architecture principles (TDD, Clean Architecture)
- Code quality standards reference (points to rules/*.md)

---

### conventions.local.md ❌ (Gitignored)

**Purpose**: Personal conventions and commit standards

**Contains**:
- Personal commit message examples
- Forbidden AI references in commits
- Personal workflow notes

---

### delegation-strategy.md ✅ (Committed)

**Purpose**: Token optimization via delegation to local tools

**Contains**:
- Delegation matrix (what to delegate, what Claude handles)
- Architecture benefits
- Performance characteristics

**See also**: [delegation.md](delegation.md)

---

## Documentation (User Guides)

**Location**: `docs/*.md`

**Purpose**: User-facing documentation for understanding and configuring the system

**Audience**: Developers using Claude Code with this setup

---

### settings.md ✅

**Purpose**: Guide for configuring models, AWS, plugins

**Personas**: Complex Reasoner, Speed Optimizer, Multi-Account User

**See**: [settings.md](settings.md)

---

### claude-instructions.md ✅

**Purpose**: Guide for configuring language, tone, shortcuts

**Personas**: Non-English Speaker, Minimalist, Power User

**See**: [claude-instructions.md](claude-instructions.md)

---

### integrations.md ✅

**Purpose**: Guide for multi-account profiles (VCS, CI, docs, issues)

**Personas**: Single Account, Multi-Account, Future-Proof

**See**: [integrations.md](integrations.md)

---

### delegation.md ✅

**Purpose**: Explain delegation architecture and token optimization

**See**: [delegation.md](delegation.md)

---

### scripts.md ✅

**Purpose**: Python scripts reference for automation

**See**: [scripts.md](scripts.md)

---

### file-structure.md ✅

**Purpose**: This file - complete organization reference

---

## Scripts (Automation)

**Location**: `scripts/`

**Purpose**: Python automation scripts for repetitive tasks

**Structure**:
```
scripts/
├── cli/           # User-facing scripts
├── common/        # Shared utilities
├── tests/         # Test suite (pytest)
└── requirements.txt
```

**See**: [scripts.md](scripts.md) for detailed reference

---

### cli/ (User-facing)

**switch-profile.py**
- Switch integration profiles (work/personal)
- See: [integrations.md](integrations.md)

**extract_issue.py**
- Extract issue ID from branch or commit

**format_commit_message.py**
- Validate and format commit messages

**search_kanban.py**
- Search KANBAN entries by issue/tag/date

**update_kanban.py**
- Update KANBAN with commits

**analyze_commit_quality.py**
- Security/quality checks (pre-commit)

---

### common/ (Shared)

**integrations.py**
- Profile loading functions
- `load_integrations()`, `get_vcs_provider()`, etc.

**models.py**
- Data models (IntegrationConfig, etc.)

**utils.py**
- Shared utilities

**constants.py**
- Shared constants

---

### tests/ (Test Suite)

**Framework**: pytest

**Run tests**:
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v
```

**Coverage**:
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Agents (Autonomous)

**Location**: `agents/*/`

**Purpose**: Specialized autonomous workflows triggered by skills or Claude

**Structure**:
```
agents/<agent-name>/
├── AGENT.md       # Agent definition
├── scripts/       # Agent-specific scripts
└── tests/         # Agent tests
```

**See**: [delegation.md](delegation.md) for workflows

---

### ci-fix-proposer

**Purpose**: CI error fix proposals using Ollama

**Trigger**: `/analyze-github-ci` skill

**Workflow**: CI failure → Extract context → Ollama proposes fix → Claude validates

---

### code-analyzer

**Purpose**: Mechanical code pattern detection

**Trigger**: `/analyze-code` skill

**Workflow**: Parallel analysis (dead code, DRY, complexity) → Aggregated report

---

### black-box-analyzer

**Purpose**: Autonomous test analysis for large projects

**Trigger**: `/analyze-tests` skill (≥50 endpoints or ≥100 test files)

**Workflow**: Detect project type → Extract entry points → Map tests → Prioritize gaps

---

### test-runner

**Purpose**: Autonomous test execution

**Trigger**: Automatic or manual

**Workflow**: Run tests → Calculate coverage → Structured report

---

## Integrations (Multi-account)

**Location**: `integrations/`

**Purpose**: Multi-environment profiles for VCS, CI, docs, issues

**Structure**:
```
integrations/
├── .active ❌              # Current profile (gitignored)
├── .gitignore ✅           # Ignores *.local.json
├── default.json ✅         # GitHub default (committed)
└── *.local.json ❌         # Personal profiles (gitignored)
```

**See**: [integrations.md](integrations.md) for complete guide

---

### default.json ✅ (Committed)

**Purpose**: Default GitHub profile for everyone

**Contains**:
```json
{
  "name": "GitHub Default",
  "vcs": { "provider": "github", "url": "https://github.com" },
  "ci": { "provider": "github-actions" },
  "docs": { "provider": "github-pages" },
  "issues": { "provider": "github", "issue_format": "#(\\d+)" }
}
```

---

### work.local.json ❌ (Gitignored)

**Purpose**: Work profile (personal)

**Example**: Work GitHub org with different settings

---

### personal.local.json ❌ (Gitignored)

**Purpose**: Personal profile (personal)

**Example**: Personal GitHub account

---

### path-mappings.local.json ❌ (Gitignored)

**Purpose**: Auto-switch profiles by directory

**Example**:
```json
{
  "mappings": [
    { "path": "C:/dev/work", "profile": "work" },
    { "path": "C:/dev/personal", "profile": "personal" }
  ]
}
```

---

## Rules (Standards)

**Location**: `rules/*.md`

**Purpose**: Coding standards automatically loaded by Claude Code

**Auto-loaded**: Yes (by Claude Code at session start)

---

### General Standards

**standards-code-quality.md** ✅
- DRY, SOLID, KISS, YAGNI principles
- No hardcoded values
- One class/enum/interface per file
- Constants over magic numbers
- No TODO/FIXME

**standards-security.md** ✅
- OWASP Top 10
- Input validation
- No hardcoded credentials
- Secure defaults

**standards-testing.md** ✅
- TDD approach
- Coverage ≥ 80%
- Prefer InMemory test doubles
- Fast, deterministic tests

---

### Language-Specific Standards

**TypeScript/JavaScript**:
- `standards-typescript.md` ✅
- `standards-javascript.md` ✅
- `standards-vuejs3.md` ✅
- `standards-kendo.md` ✅

**Markup/Templates**:
- `standards-cshtml.md` ✅

**Scripting**:
- `standards-bash.md` ✅
- `standards-powershell.md` ✅

**Infrastructure**:
- `standards-docker.md` ✅
- `standards-kubernetes.md` ✅
- `standards-terraform.md` ✅

**Database**:
- `standards-postgresql.md` ✅
- `standards-sqlserver.md` ✅

---

## Skills (User-invocable)

**Location**: `skills/*/`

**Purpose**: User-invocable commands triggered via `/skill-name`

**Structure**:
```
skills/<skill-name>/
├── SKILL.md       # Skill definition
├── scripts/       # Skill-specific scripts (optional)
└── tests/         # Skill tests (optional)
```

---

### analyze-github-ci

**Trigger**: `/analyze-github-ci`

**Action**: Launches `ci-fix-proposer` agent

---

### analyze-code

**Trigger**: `/analyze-code`

**Action**: Launches `code-analyzer` agent

---

### analyze-tests

**Trigger**: `/analyze-tests`

**Action**: Launches `black-box-analyzer` agent (≥50 endpoints or ≥100 test files)

---

### analyze-commit

**Trigger**: `/analyze-commit`

**Action**: Runs `analyze_commit_quality.py` script

---

### update-context

**Trigger**: `/update-context`

**Action**: Updates KANBAN.md and ARCHITECTURE.md

---

## Gitignore Patterns

**Location**: `.gitignore`

**Purpose**: Exclude personal/private files from git

**Key patterns**:
```gitignore
# Personal files
*.local.*                    # All .local.* files
CLAUDE.local.md
settings.local.json
contexts/*.local.md

# Integration profiles
integrations/.active
integrations/*.local.json
integrations/path-mappings.local.json

# Auto-memory
projects/*/memory/

# Security logs
security/
security_warnings_state_*.json

# Plugins
plugins/

# Test artifacts
__pycache__/
*.pyc
.pytest_cache/
.coverage

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Large session transcripts
projects/**/*.jsonl
```

**Convention**: `*.local.*` files are always gitignored (personal)

---

## Public vs Private Files

### Public Files ✅ (Committed)

**Team-shared configuration**:
- CLAUDE.md, settings.json
- contexts/*.md (except *.local.md)
- docs/*.md
- scripts/cli/*.py, scripts/common/*.py
- agents/*/AGENT.md, agents/*/scripts/*.py
- integrations/default.json
- rules/*.md
- skills/*/SKILL.md

**Can reference**: Other public files only

---

### Private Files ❌ (Gitignored)

**Personal configuration**:
- *.local.* (CLAUDE.local.md, settings.local.json, contexts/*.local.md)
- integrations/.active
- integrations/*.local.json
- integrations/path-mappings.local.json

**Can reference**: Both public and private files

**NEVER**: Public files referencing .local.* files

---

## Load Sequence

**Claude Code automatically reads at session start**:

1. `~/.claude/settings*.json` (global permissions)
2. `~/.claude/CLAUDE.md` (global instructions)
3. `<project>/.claude/settings*.json` (project permissions)
4. `<project>/.claude/CLAUDE.md` (project instructions)
5. `<project>/.claude/rules/**/*.md` (auto-loaded patterns)
6. `README.md`, `docs/*.md` (project documentation)

**All automatic, transparent, graceful if missing.**

**See**: [claude-instructions.md](claude-instructions.md) for load sequence diagram

---

## Cross-References

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  File/Folder             Primary Documentation                  │
│  ──────────────────────────────────────────────────────────     │
│  CLAUDE.md/local.md   →  docs/claude-instructions.md            │
│  settings.json/local  →  docs/settings.md                       │
│  integrations/        →  docs/integrations.md                   │
│  scripts/             →  docs/scripts.md                        │
│  agents/              →  docs/delegation.md                     │
│  contexts/            →  This file + README.md                  │
│  rules/               →  contexts/conventions.md                │
│  skills/              →  README.md                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Common Questions

**Q: Which files should I edit?**  
A: Start with `CLAUDE.local.md` and `settings.local.json` for personal preferences. Never edit public files unless you mean to change team defaults.

**Q: How do I add a new integration profile?**  
A: Create `integrations/<name>.local.json` and run `python scripts/cli/switch-profile.py <name>`. See [integrations.md](integrations.md).

**Q: Where are tests for scripts?**  
A: `scripts/tests/test_*.py`. Run with `cd ~/.claude/scripts && python -m pytest tests/ -v`.

**Q: How do I add a new coding standard?**  
A: Create `rules/standards-<name>.md`. It will be auto-loaded by Claude Code.

**Q: Can I delete contexts/*.md files?**  
A: No - these are auto-loaded by Claude Code. You can add `.local.md` files for personal notes.

**Q: What's the difference between docs/ and contexts/?**  
A: `docs/` = User documentation (how to configure). `contexts/` = AI context (what Claude auto-loads).

**Q: Are scripts cross-platform?**  
A: Yes - Python scripts use `pathlib` for cross-platform paths.

**Q: How do I know which agents exist?**  
A: Check `agents/*/AGENT.md` files or see [delegation.md](delegation.md).

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Category            Location              Committed?           │
│  ──────────────────────────────────────────────────────────     │
│  Team config         CLAUDE.md             ✅ Yes               │
│  Personal config     CLAUDE.local.md       ❌ No (gitignored)  │
│  Team settings       settings.json         ✅ Yes               │
│  Personal settings   settings.local.json   ❌ No (gitignored)  │
│  Work history        contexts/kanban.md    ✅ Yes               │
│  Personal notes      *.local.md            ❌ No (gitignored)  │
│  User guides         docs/*.md             ✅ Yes               │
│  Automation          scripts/cli/*.py      ✅ Yes               │
│  Agents              agents/*/AGENT.md     ✅ Yes               │
│  Profiles (default)  integrations/default  ✅ Yes               │
│  Profiles (custom)   integrations/*.local  ❌ No (gitignored)  │
│  Standards           rules/*.md            ✅ Yes               │
│  Skills              skills/*/SKILL.md     ✅ Yes               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

**Remember**: Public files (committed) for team, `*.local.*` files (gitignored) for personal. Public files never reference `.local.*` files. CLAUDE.local.md is the entry point for all personal `.local.md` files.
