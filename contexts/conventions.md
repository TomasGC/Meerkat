# Conventions - Meerkat

---

## Commit Format

**Format**: `#ISSUE: type: description`

**`docs` exception**: `docs: description` — documentation commits never carry an
issue number, no exceptions.

**Types**: feat, fix, refactor, test, docs, chore

**Examples**:
```
#3: feat: add typed-agents mode to library analyzer
#3: fix: resolve common namespace collision in pytest
#3: refactor: reorganize test suite into 4-tier co-located structure
#1: feat: add universal black-box test analyzer agent
docs: document BBA analysis result cache
```

**Rules**:
- Always prefix with issue number, except `docs` commits which never have one
- Description: WHAT/WHY, not HOW/WHO
- No stats (+XX lines), no implementation details, no emoji

**Bad**: `#3: feat: add caching (+806 lines) 🎉`
**Good**: `#3: feat: add system information caching for faster page loads`
**Bad**: `#24: docs: document the cache`
**Good**: `docs: document the cache`

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

### Model Configuration

- All model names live in `configs/local_models_config.json` only — never hardcoded in scripts or agents
- `scripts/model_config.py`: singleton reader; `get_model(role, provider="local")` resolves role → model name
- `scripts/model_utils.py`: shared local AI client; imported via shims at `agents/*/scripts/common/model_utils.py`
- Roles: `analyzer`, `fast`, `deep`, `reasoning`, `guard`

### CCA (Clean Code Analyzer)
- Default role: `analyzer` (semantic checkers: SOLID, KISS, YAGNI, CQRS, DDD, SLAP)
- Fast mode: `--fast` passes `role="fast"` to checkers
- Tests run via `python -m pytest` directly from `agents/clean-code-analyzer/scripts/`
- Prompts in `scripts/prompts/local/` (6 templates) and `scripts/prompts/claude/` (6 fallback templates)
- Test naming: `tests/unit/` (singular), `tests/integration/mock/`, `tests/integration/real/` — differs from the global `units/`/`integration-mocks/` convention

