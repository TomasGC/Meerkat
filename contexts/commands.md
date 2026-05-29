# Commands - Claude Code Global Scripts

Commands for managing `~/.claude/` configuration and scripts.

---

## Scripts Tests

Run tests for Python scripts in `~/.claude/scripts/`:

### Quick validation (before commit)
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v --maxfail=1
```

### Full test suite
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v
```

### With coverage report
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

### Specific test modules
```bash
# Integration profiles
cd ~/.claude/scripts && python -m pytest tests/test_integrations.py -v

# Issue extraction
cd ~/.claude/scripts && python -m pytest tests/test_extract_issue.py -v

# Commit message formatting
cd ~/.claude/scripts && python -m pytest tests/test_format_commit_message.py -v

# KANBAN search
cd ~/.claude/scripts && python -m pytest tests/test_search_kanban.py -v

# KANBAN update
cd ~/.claude/scripts && python -m pytest tests/test_update_kanban.py -v
```

### Fast tests only (skip slow integration tests)
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v -m "not slow"
```

### Syntax validation
```bash
cd ~/.claude/scripts && python -m py_compile cli/*.py common/*.py
```

---

## Integration Profiles

Manage VCS/CI/docs/issues provider profiles:

### Switch profile
```bash
cd ~/.claude/scripts && python cli/switch-profile.py <profile-name>
```

### List available profiles
```bash
cd ~/.claude/scripts && python cli/switch-profile.py --list
```

### Show active profile status
```bash
cd ~/.claude/scripts && python cli/switch-profile.py --status
```

### Validate profile JSON
```bash
cd ~/.claude/scripts && python cli/switch-profile.py --validate <profile-name>
```

### Create new profile
```bash
cd ~/.claude/scripts && python cli/switch-profile.py --create <profile-name>
```

---

## Issue Management

Extract and format issue IDs from branches/commits:

### Extract issue from current branch
```bash
cd ~/.claude/scripts && python cli/extract_issue.py
```

### Extract from specific branch
```bash
cd ~/.claude/scripts && python cli/extract_issue.py --branch "feature/#123-auth"
```

### Extract from last commit
```bash
cd ~/.claude/scripts && python cli/extract_issue.py --from-commit
```

---

## Commit Message Formatting

Validate and format commit messages:

### Validate commit message
```bash
cd ~/.claude/scripts && python cli/format_commit_message.py --validate --message "#123: feat: add auth"
```

### Generate suggestion for invalid message
```bash
cd ~/.claude/scripts && python cli/format_commit_message.py --suggest --message "added authentication"
```

### Format commit message
```bash
cd ~/.claude/scripts && python cli/format_commit_message.py --issue "#123" --type feat --message "add authentication"
```

---

## KANBAN Management

Search and update KANBAN entries:

### Search KANBAN by issue
```bash
cd ~/.claude/scripts && python cli/search_kanban.py --issue "#123"
```

### Search by tag
```bash
cd ~/.claude/scripts && python cli/search_kanban.py --tag "optimization"
```

### Search by date range
```bash
cd ~/.claude/scripts && python cli/search_kanban.py --from "2026-05-01" --to "2026-05-31"
```

### Update KANBAN (auto-detect issue + commits)
```bash
cd ~/.claude/scripts && python cli/update_kanban.py --auto
```

### Update with specific issue and commits
```bash
cd ~/.claude/scripts && python cli/update_kanban.py --issue "#123" --commits "abc123f,def456a"
```

---

## Session Context Loading

Load project context at session start:

### Load context for current branch
```bash
cd ~/.claude/scripts && python cli/load_session_context.py
```

---

## Validation

Pre-commit validation checks:

### Run all validations
```bash
cd ~/.claude/scripts && python -m pytest tests/ -v --maxfail=1
```

### Quick syntax check
```bash
cd ~/.claude/scripts && python -m py_compile cli/*.py common/*.py
```
