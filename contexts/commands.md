# Commands - Meerkat Scripts

Commands for `~/.claude/` scripts and tests.

---

## Clean Code Analyzer (CCA)

### Analyze a project

```bash
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --full
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --checks solid,dry
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --format table
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --fast
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --model qwen2.5-coder:14b
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --no-cache
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --clear-cache
```

**Flags**:
- (no flags) — incremental: branch-vs-main changed files only
- `--full` — analyze entire repo
- `--checks solid,dry` — run specific principles only
- `--fast` — use qwen2.5-coder:7b (faster, lower quality)
- `--model MODEL` — override Ollama model for semantic checkers
- `--no-cache` — bypass per-file content-hash cache
- `--agents N` — N independent Ollama calls per file, dedup-merged

### CCA tests

```bash
cd ~/.claude/agents/clean-code-analyzer/scripts
python -m pytest tests/unit/ -q
python -m pytest tests/integration/mock/ -q
python -m pytest tests/unit/ tests/integration/mock/ --cov=checkers --cov=common --cov=orchestrate -q
```

---

## Tests

### Run by tier (from ~/.claude/)
```bash
pytest agents/black-box-analyzer/tests/units/ -v
pytest agents/black-box-analyzer/tests/integration-mocks/ -v
pytest agents/black-box-analyzer/tests/integration-reals/ -v
pytest agents/black-box-analyzer/tests/e2e/ -v

pytest scripts/cli/tests/units/ -v
pytest scripts/cli/tests/integration-mocks/ -v
pytest scripts/common/tests/units/ -v
pytest scripts/tests/e2e/ -v
```

### Run by marker (avoid BBA + scripts together — common namespace collision)
```bash
# BBA only
pytest agents/black-box-analyzer/tests -m units
pytest agents/black-box-analyzer/tests -m "units or integration_mocks"

# Scripts only
pytest scripts/tests scripts/cli/tests scripts/common/tests -m units
```

### CI-safe (no real Ollama required)
```bash
pytest agents/black-box-analyzer/tests -m "units or integration_mocks"
pytest scripts/tests scripts/cli/tests scripts/common/tests -m "units or integration_mocks"
```

### Full suites (separate invocations)
```bash
pytest agents/black-box-analyzer/tests -v
pytest scripts/tests scripts/cli/tests scripts/common/tests -v
```

---

## Integration Profiles

```bash
python scripts/cli/switch-profile.py --list
python scripts/cli/switch-profile.py <profile-name>
python scripts/cli/switch-profile.py --status
python scripts/cli/switch-profile.py --validate <profile-name>
```

---

## Issue / Commit Utilities

```bash
# Extract issue from current branch
python scripts/cli/extract_issue.py

# Validate commit message
python scripts/cli/format_commit_message.py --validate --message "#3: feat: add thing"

# Format commit message
python scripts/cli/format_commit_message.py --issue "#3" --type feat --message "add thing"
```

---

## KANBAN

```bash
python scripts/cli/search_kanban.py --issue "#3"
python scripts/cli/search_kanban.py --tag "testing"
python scripts/cli/update_kanban.py --auto
```

---

## Syntax Check

```bash
python -m py_compile scripts/cli/*.py scripts/common/*.py
```
