# Python Scripts Guide

> **TL;DR**: Automation scripts in `~/.claude/scripts/` for integration profiles, issue extraction, KANBAN updates, and more. Run with `python ~/.claude/scripts/cli/script-name.py`.

---

## Why These Scripts

```
Without Scripts                With Scripts
───────────────                ────────────
Manual profile switching   →   One command
Manual issue extraction    →   Auto-detect from branch
Manual KANBAN updates      →   Auto-update with commits
Manual commit validation   →   Pre-commit hook

Problem:                       Solution:
Repetitive manual tasks    →   Automated workflows
```

**Golden rule**: Scripts handle mechanical operations. You focus on code.

---

## Quick Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `switch-profile.py` | Switch integration profiles | `python switch-profile.py work` |
| `extract_issue.py` | Extract issue from branch/commit | `python extract_issue.py` |
| `format_commit_message.py` | Format/validate commit messages | `python format_commit_message.py --validate` |
| `search_kanban.py` | Search KANBAN entries | `python search_kanban.py --issue "#123"` |
| `update_kanban.py` | Update KANBAN (auto-detect) | `python update_kanban.py --auto` |
| `analyze_commit_quality.py` | Security/quality checks | `python analyze_commit_quality.py` |

**Full commands**: See `contexts/commands.md`

---

## Scripts Overview

### Integration Profiles

**Script**: `switch-profile.py`

**Purpose**: Switch between work/personal/custom integration profiles

```bash
# Switch to work profile
python ~/.claude/scripts/cli/switch-profile.py work

# List all profiles
python ~/.claude/scripts/cli/switch-profile.py --list

# Show current profile
python ~/.claude/scripts/cli/switch-profile.py
```

**Details**: See `docs/integrations.md`

---

### Issue Management

**Script**: `extract_issue.py`

**Purpose**: Extract issue ID from branch name or commit message

```bash
# Extract from current branch
python ~/.claude/scripts/cli/extract_issue.py

# Extract from specific branch
python ~/.claude/scripts/cli/extract_issue.py --branch "feature/#123-auth"

# Extract from last commit
python ~/.claude/scripts/cli/extract_issue.py --from-commit
```

**Output**:
```json
{
  "success": true,
  "issue_id": "#123",
  "source": "branch_name"
}
```

---

### Commit Message Formatting

**Script**: `format_commit_message.py`

**Purpose**: Validate and format commit messages according to standards

```bash
# Validate commit message
python ~/.claude/scripts/cli/format_commit_message.py \
  --validate \
  --message "#123: feat: add auth"

# Generate suggestion for invalid message
python ~/.claude/scripts/cli/format_commit_message.py \
  --suggest \
  --message "added authentication"

# Format commit message
python ~/.claude/scripts/cli/format_commit_message.py \
  --issue "#123" \
  --type feat \
  --message "add authentication"
```

**Valid types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

---

### KANBAN Management

**Script**: `search_kanban.py`

**Purpose**: Search KANBAN entries by issue, tag, or date

```bash
# Search by issue
python ~/.claude/scripts/cli/search_kanban.py --issue "#123"

# Search by tag
python ~/.claude/scripts/cli/search_kanban.py --tag "optimization"

# Search by date range
python ~/.claude/scripts/cli/search_kanban.py \
  --from "2026-05-01" \
  --to "2026-05-31"
```

---

**Script**: `update_kanban.py`

**Purpose**: Update KANBAN with issue progress and commits

```bash
# Auto-detect issue + commits (recommended)
python ~/.claude/scripts/cli/update_kanban.py --auto

# Specify issue and commits
python ~/.claude/scripts/cli/update_kanban.py \
  --issue "#123" \
  --commits "abc123f,def456a"
```

---

### Code Quality Analysis

**Script**: `analyze_commit_quality.py`

**Purpose**: Security and quality checks on commit changes

```bash
# Analyze current changes
python ~/.claude/scripts/cli/analyze_commit_quality.py

# Analyze specific files
python ~/.claude/scripts/cli/analyze_commit_quality.py --files "src/**/*.py"
```

**Checks**:
- Hardcoded secrets (API keys, passwords)
- SQL injection patterns
- XSS vulnerabilities
- Magic numbers
- TODO/FIXME markers
- console.log statements

**Use case**: Pre-commit hook validation

---

## Testing Scripts

**Location**: `~/.claude/scripts/tests/`

**Framework**: pytest

```bash
# Run all tests
cd ~/.claude/scripts && python -m pytest tests/ -v

# Quick validation (before commit)
cd ~/.claude/scripts && python -m pytest tests/ -v --maxfail=1

# With coverage
cd ~/.claude/scripts && python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Specific test
cd ~/.claude/scripts && python -m pytest tests/test_integrations.py -v
```

**See**: `contexts/commands.md` for full test commands

---

## Common Workflows

### Workflow 1: Switch Profile for Work Project

```bash
# Switch to work profile
python ~/.claude/scripts/cli/switch-profile.py work

# Verify active profile
python ~/.claude/scripts/cli/switch-profile.py
```

---

### Workflow 2: Commit with Issue ID

```bash
# 1. Extract issue from branch
issue=$(python ~/.claude/scripts/cli/extract_issue.py --format json | jq -r '.issue_id')

# 2. Format commit message
python ~/.claude/scripts/cli/format_commit_message.py \
  --issue "$issue" \
  --type feat \
  --message "add user authentication"

# 3. Validate before committing
python ~/.claude/scripts/cli/format_commit_message.py \
  --validate \
  --message "#123: feat: add user authentication"
```

---

### Workflow 3: Update KANBAN After Work

```bash
# Auto-detect issue + all commits since last update
python ~/.claude/scripts/cli/update_kanban.py --auto
```

---

### Workflow 4: Pre-Commit Quality Check

```bash
# Run security/quality checks
python ~/.claude/scripts/cli/analyze_commit_quality.py

# If pass → commit
# If fail → fix issues first
```

---

## Script Architecture

### Common Modules

**Location**: `~/.claude/scripts/common/`

```
common/
├── integrations.py     # Profile loading (load_integrations)
├── models.py           # Data models (IntegrationConfig, etc.)
├── utils.py            # Shared utilities
└── constants.py        # Shared constants
```

**Import example**:
```python
from common.integrations import load_integrations

config = load_integrations()
print(config.vcs_provider)  # github
```

---

### CLI Scripts

**Location**: `~/.claude/scripts/cli/`

**Pattern**: Each script is standalone with argparse CLI

```python
#!/usr/bin/env python3
"""Script description."""

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--arg", help="...")
    args = parser.parse_args()
    
    # Implementation
    
if __name__ == "__main__":
    main()
```

---

## Troubleshooting

### Script not found

```bash
# Check script exists
ls ~/.claude/scripts/cli/script-name.py

# Run from correct directory
cd ~/.claude/scripts
python cli/script-name.py
```

---

### Import errors

```bash
# Install dependencies
cd ~/.claude/scripts
pip install -r requirements.txt

# Check Python version (3.12+ required)
python --version
```

---

### Profile not switching

```bash
# Check profiles exist
ls ~/.claude/integrations/*.json

# Check active profile
cat ~/.claude/integrations/.active

# Force switch
python ~/.claude/scripts/cli/switch-profile.py work --force
```

---

## FAQ

**Q: Where are scripts located?**  
A: `~/.claude/scripts/cli/` for user-facing scripts, `~/.claude/scripts/common/` for shared modules.

**Q: Python version required?**  
A: Python 3.12+ (uses type hints, dataclasses, pattern matching).

**Q: Do scripts work on Windows?**  
A: Yes. Use `pathlib` for cross-platform paths.

**Q: How do I add a new script?**  
A: Create in `cli/`, follow existing patterns, add tests in `tests/`, update this doc.

**Q: Can scripts be run in CI?**  
A: Yes. Example: Pre-commit hooks, GitHub Actions workflows.

**Q: Are there integration tests?**  
A: Yes. `tests/test_integrations.py`, `tests/test_extract_issue.py`, etc.

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Script                       Purpose                          │
│  ──────────────────────────────────────────────────────────    │
│  switch-profile.py         Switch integration profiles         │
│  extract_issue.py          Extract issue from branch/commit    │
│  format_commit_message.py  Validate/format commit messages     │
│  search_kanban.py          Search KANBAN entries               │
│  update_kanban.py          Update KANBAN with commits          │
│  analyze_commit_quality.py Security/quality checks             │
│                                                                │
│  All scripts:                                                  │
│  - Located in ~/.claude/scripts/cli/                           │
│  - Python 3.12+ required                                       │
│  - Cross-platform (pathlib)                                    │
│  - Have tests in tests/                                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- **Commands Reference**: `contexts/commands.md` - Full script commands with examples
- **Integrations Guide**: `docs/integrations.md` - Profile system explained
- **Delegation Guide**: `docs/delegation.md` - How scripts fit in automation
- **Architecture**: `contexts/architecture.md` - System overview

---

**Remember**: Scripts are automation tools. Use them to eliminate repetitive tasks. They're tested (99%+ coverage) and cross-platform.
