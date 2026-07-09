---
description: Meerkat CLI script commands for tests, profiles, KANBAN, and validation
paths: ["**/.claude/**"]
---

# Commands - Claude Code Global Scripts

Commands for managing `~/.claude/` configuration and scripts.

---

## Scripts Tests

```bash
# Quick validation
cd ~/.claude/scripts && python -m pytest tests/ -v --maxfail=1

# Full suite
cd ~/.claude/scripts && python -m pytest tests/ -v

# With coverage
cd ~/.claude/scripts && python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Fast only
cd ~/.claude/scripts && python -m pytest tests/ -v -m "not slow"

# Syntax check
cd ~/.claude/scripts && python -m py_compile cli/*.py common/*.py
```

---

## Integration Profiles

```bash
cd ~/.claude/scripts && python cli/switch-profile.py --list
cd ~/.claude/scripts && python cli/switch-profile.py <profile-name>
cd ~/.claude/scripts && python cli/switch-profile.py --status
```

---

## KANBAN Management

```bash
cd ~/.claude/scripts && python cli/update_kanban.py --auto
cd ~/.claude/scripts && python cli/search_kanban.py --issue "#123"
```

---

## Issue Management

```bash
cd ~/.claude/scripts && python cli/extract_issue.py
cd ~/.claude/scripts && python cli/extract_issue.py --branch "feature/#123-auth"
```
