# Conventions - Claude Code Standards

Project structure, file organization, and development principles.

---

## Commit Format

**Format**: `#ISSUE: type: description`

**Types**: feat, fix, refactor, test, docs, chore

**Examples**:
```
#1: feat: add universal black-box test analyzer
#1: fix: resolve UTF-8 encoding in pipeline scripts
#1: refactor: extract repository pattern for cleaner architecture
#1: docs: update integration profiles documentation
```

**Rules**:
- Always prefix with GitHub issue number
- Description: WHAT/WHY, not HOW/WHO
- No stats (+XX lines), no implementation details, no emoji

---

## Branch Naming

- Features: `feature/#ISSUE-description`
- Bugfixes: `bugfix/#ISSUE-description`

---

## File Organization

### .claude/ Directory Structure

```
<project_root>/
├── .claude/
│   ├── CLAUDE.md                    # Project instructions (shared)
│   ├── CLAUDE.local.md              # Personal overrides (gitignored)
│   ├── settings.json                # Project settings (shared)
│   ├── settings.local.json          # Local settings (gitignored)
│   ├── contexts/                    # Context files (auto-loaded)
│   │   ├── kanban.md                # Task tracking (shared)
│   │   ├── kanban.local.md          # Personal notes (gitignored)
│   │   ├── architecture.md          # Architecture (shared)
│   │   ├── commands.md              # Build/test commands (shared)
│   │   └── conventions.md           # This file (shared)
│   ├── rules/                       # Auto-loaded coding standards
│   │   └── standards-*.md
│   ├── skills/                      # Custom skills
│   ├── agents/                      # Custom agents
│   └── hooks/                       # Automation hooks
```

**Pattern**: `.local.*` files are gitignored (personal), base files are committed (shared).

---

## Code Quality

See `~/.claude/rules/standards-*.md` for language-specific standards.

**Principles**: TDD, Clean Architecture, DRY, SOLID, KISS, YAGNI
**Coverage**: ≥ 80%
**No**: hardcoded values, TODO/FIXME, magic numbers
