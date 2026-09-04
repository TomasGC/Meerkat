# Conventions - Meerkat

---

## Commit Format

**Format**: `#ISSUE: type: description`

**Types**: feat, fix, refactor, test, docs, chore

**Examples**:
```
#3: feat: add typed-agents mode to library analyzer
#3: fix: resolve common namespace collision in pytest
#3: refactor: reorganize test suite into 4-tier co-located structure
#1: feat: add universal black-box test analyzer agent
```

**Rules**:
- Always prefix with issue number
- Description: WHAT/WHY, not HOW/WHO
- No stats (+XX lines), no implementation details, no emoji

**Bad**: `#3: feat: add caching (+806 lines) 🎉`
**Good**: `#3: feat: add system information caching for faster page loads`

---

## Branch Naming

- Features: `feature/#ISSUE-description`
- Bugfixes: `bugfix/#ISSUE-description`

---

## Python Conventions

- Python 3.12+
- One class per file
- No hardcoded values — constants or config
- No TODO/FIXME — fix or create issue
- Type annotations on public functions

---

## Agent Conventions

### CCA (Clean Code Analyzer)
- Default model: `devstral` (semantic checkers: SOLID, KISS, YAGNI, CQRS, DDD, SLAP)
- Fast model: `qwen2.5-coder:7b` (via `--fast`)
- Tests run via `python -m pytest` directly from `agents/clean-code-analyzer/scripts/`
- Prompts in `scripts/prompts/ollama/` (6 templates) and `scripts/prompts/claude/` (6 fallback templates)
- Test naming: `tests/unit/` (singular), `tests/integration/mock/`, `tests/integration/real/` — differs from the global `units/`/`integration-mocks/` convention

