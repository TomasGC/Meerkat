# Claude Code - Personal Configuration

> **TL;DR**: Personal Claude Code setup with optimized workflows, multi-environment profiles, and automated delegation for token efficiency.

---

## What Is This?

This is your **personal Claude Code configuration** (`~/.claude/`) containing:

- **Instructions** (CLAUDE.md) → How Claude behaves
- **Settings** (settings.json) → What tools Claude uses
- **Contexts** (contexts/*.md) → Project knowledge (KANBAN, architecture, etc.)
- **Scripts** (scripts/*.py) → Automation tools
- **Agents** (agents/*/) → Specialized autonomous workflows
- **Documentation** (docs/*.md) → User guides

**Goal**: Consistent, efficient, personalized Claude Code experience across all projects.

---

## Prerequisites

| Tool | Required | Purpose |
|------|----------|---------|
| Node.js 18+ | ✅ | npm + JS/TS project templates |
| Claude Code | ✅ | Core CLI |
| Python 3.12+ | ✅ | Automation scripts |
| Git | ✅ | Version control |
| uv | ⭐ | Fast package manager |
| Ollama | ⭐ | Local model delegation |

→ **Full install guide (per OS)**: [docs/setup.md](docs/setup.md)

---

## Quick Start (3 Minutes)

### First Time Setup

```bash
# 1. Clone/setup already done ✅
cd ~/.claude

# 2. Review your personal preferences (optional)
vim CLAUDE.local.md  # Language, tone, shortcuts

# 3. Configure model/AWS if needed (optional)
vim settings.local.json  # Opus, personal AWS profile

# 4. Start using Claude Code
# Everything works with team defaults!
```

**Zero configuration required** - Team defaults work perfectly out of the box.

---

## Documentation Index

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  What You Want                Where to Look                     │
│  ──────────────────────────────────────────────────────────     │
│  Change model/AWS          →  docs/settings.md                  │
│  Change language/tone      →  docs/claude-instructions.md       │
│  Multi-account setup       →  docs/integrations.md              │
│  Understand delegation     →  docs/delegation.md                │
│  Use automation scripts    →  docs/scripts.md                   │
│  Understand file structure →  docs/file-structure.md            │
│                                                                 │
│  Quick commands            →  contexts/commands.md              │
│  Architecture details      →  contexts/architecture.md          │
│  Work history              →  contexts/kanban.md                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Guides

| Guide | Purpose | When You Need It |
|-------|---------|------------------|
| **[settings.md](docs/settings.md)** | Configure models, AWS, plugins | Want Opus, personal AWS, or plugin changes |
| **[claude-instructions.md](docs/claude-instructions.md)** | Configure language, tone, shortcuts | Want French conversation or concise responses |
| **[integrations.md](docs/integrations.md)** | Multi-account profiles (VCS, CI, issues) | Work + Personal GitHub accounts |
| **[delegation.md](docs/delegation.md)** | Token optimization via local tools | Understand how delegation saves tokens |
| **[scripts.md](docs/scripts.md)** | Automation scripts reference | Use Python scripts for automation |
| **[file-structure.md](docs/file-structure.md)** | Complete organization of ~/.claude/ | Understand what each file/folder does |

---

## Quick Links

### Configuration Files

```
CLAUDE.md              # Team rules (how to behave)
CLAUDE.local.md        # Your preferences (language, tone)
settings.json          # Team defaults (models, plugins)
settings.local.json    # Your overrides (Opus, AWS)
```

### Contexts (Auto-loaded)

```
contexts/kanban.md           # Work history
contexts/architecture.md     # Meerkat delegation architecture
contexts/commands.md         # Script commands reference
contexts/conventions.md      # File structure & principles
contexts/delegation-strategy.md  # Token optimization rules
```

### Documentation (User Guides)

```
docs/settings.md                # Models, AWS, plugins
docs/claude-instructions.md     # Language, tone, shortcuts
docs/integrations.md            # VCS/CI/issues profiles
docs/delegation.md              # Delegation architecture
docs/scripts.md                 # Python scripts guide
docs/file-structure.md          # Complete file organization
```

---

## Common Tasks

### Change Language

```markdown
<!-- ~/.claude/CLAUDE.local.md -->
## Communication Preferences

**Conversation**: French
**Code/Docs/Commits**: English
```

**Details**: See [claude-instructions.md](docs/claude-instructions.md)

---

### Change Model

```json
// ~/.claude/settings.local.json
{
  "model": "opus"
}
```

**Details**: See [settings.md](docs/settings.md)

---

### Add Personal AWS Profile

```json
// ~/.claude/settings.local.json
{
  "awsAuthRefresh": "aws sso login --profile my-profile",
  "env": {
    "AWS_PROFILE": "my-profile",
    "AWS_REGION": "eu-west-1"
  }
}
```

**Details**: See [settings.md](docs/settings.md)

---

### Switch Integration Profile (Work/Personal)

```bash
python ~/.claude/scripts/cli/switch-profile.py work
```

**Details**: See [integrations.md](docs/integrations.md)

---

### Run Script Tests

```bash
cd ~/.claude/scripts && python -m pytest tests/ -v
```

**Details**: See [contexts/commands.md](contexts/commands.md)

---

## File Structure Overview

```
~/.claude/
│
├── README.md                    # This file
│
├── Configuration
├── CLAUDE.md                    # Team instructions (committed)
├── CLAUDE.local.md              # Your instructions (gitignored)
├── settings.json                # Team settings (committed)
├── settings.local.json          # Your settings (gitignored)
│
├── contexts/                    # Auto-loaded context
│   ├── kanban.md                # Work history
│   ├── architecture.md          # System architecture
│   ├── commands.md              # Script commands
│   ├── conventions.md           # File structure & principles
│   └── delegation-strategy.md   # Token optimization
│
├── docs/                        # User documentation
│   ├── settings.md              # Configuration guide
│   ├── claude-instructions.md   # Behavior guide
│   ├── integrations.md          # Multi-account guide
│   ├── delegation.md            # Delegation architecture
│   ├── scripts.md               # Scripts reference
│   └── file-structure.md        # Complete organization
│
├── scripts/                     # Automation
│   ├── cli/                     # User-facing scripts
│   ├── common/                  # Shared utilities
│   └── tests/                   # Test suite
│
├── agents/                      # Autonomous workflows
│   ├── ci-fix-proposer/
│   ├── code-analyzer/
│   ├── black-box-analyzer/
│   └── test-runner/
│
├── integrations/                # Multi-account profiles
│   ├── default.json             # GitHub (committed)
│   ├── work.json                # Work profile (gitignored)
│   └── personal.json            # Personal profile (gitignored)
│
└── rules/                       # Coding standards
    ├── standards-code-quality.md
    ├── standards-security.md
    └── standards-*.md
```

**Full details**: See [file-structure.md](docs/file-structure.md)

---

## What's Unique About This Setup?

### 1. Multi-Environment Profiles
Switch between work/personal accounts instantly without code changes.

### 2. Token Optimization via Delegation
Mechanical tasks → Local tools (Ollama, Python scripts) = 60-70% token savings.

### 3. Extensible Architecture
Ready for future providers (GitLab, Azure DevOps) with zero refactoring.

### 4. Comprehensive Documentation
Every system explained with personas, examples, and troubleshooting.

---

## Getting Help

1. **Check documentation**: See Documentation Index above
2. **Search contexts**: KANBAN.md, ARCHITECTURE.md for history
3. **Run validations**: `python ~/.claude/scripts/cli/validate-*.py`
4. **Ask in team chat**: Share specific docs link

---

## Contributing

This is a **personal configuration** but follows team standards:

- **CLAUDE.md** = Team rules (discuss before changing)
- **CLAUDE.local.md** = Your preferences (customize freely)
- **docs/*** = Documentation (improve and expand)
- **scripts/*** = Automation (add tests when adding features)

---

## Key Principles

1. **Zero config by default** - Team defaults work for 90%
2. **Customize only when needed** - Language, model, AWS, profiles
3. **Documentation first** - Every system has a guide
4. **Test everything** - Scripts have 99%+ test coverage
5. **Delegate mechanical tasks** - Optimize tokens via local tools

---

**Last Updated**: 2026-05-28  
**Version**: 2.0
