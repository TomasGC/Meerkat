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
- Style: black + isort, line length 120 (`pyproject.toml`, `.flake8`): the settings Condor's lint gate applies (#48)
- No blanket suppression. A re-export is declared in `__all__`, not hidden behind `# noqa: F401`; `# noqa`,
  `# type: ignore[code]` and `# nosec` name their reason on the same line. E402 is allowed only where a file runs as a
  script and must put `scripts/` on `sys.path` first (per-file list in `.flake8`)
- A fixture requested only for its side effect is `@pytest.mark.usefixtures("name")`, not an unused argument
- A test patches the call site the code really uses (`lib.utils.subprocess.run` for `run_command`), not a module
  attribute the code never reads
- A bug a test exposes but the change does not fix: the test asserts the right behaviour and carries
  `@pytest.mark.xfail(strict=True, reason="bug (#N): ...")` with an issue; strict mode fails the run once it is fixed

---

## Test Layout

One layout for every component (#46): agents, skills, plugins, `scripts/lib`, `scripts/cli`.

```
<component>/tests/{unit,integration_mock,integration_real,e2e,fixtures}/
```

- Tier directory name = marker name (`unit`, `integration_mock`, `integration_real`, `e2e`), applied by the
  root `conftest.py`; no explicit tier marks in test files
- Test data in `tests/fixtures/` (subdir per tier when useful), never inside a tier directory
- Tests spanning several components: root `tests/<tier>/`
- One `pytest.ini`, at the repo root; only conftests touch `sys.path`
- Details: `contexts/tests.md`

---

## Agent Conventions

### Model Configuration

- All model names live in `configs/local_models_config.json` only — never hardcoded in scripts or agents
- `scripts/lib/config/model_config.py`: singleton reader; `get_model(role, provider="local")` resolves role → model name
- `scripts/lib/ai/model_utils.py`: shared local AI client; imported via shims at `agents/*/scripts/<pkg>/model_utils.py` (`cca`, `ssa`, `bba`)
- Roles: `analyzer`, `fast`, `deep`, `reasoning`, `guard`

### CCA (Clean Code Analyzer)
- Default role: `analyzer` (semantic checkers: SOLID, KISS, YAGNI, CQRS, DDD, SLAP)
- Fast mode: `--fast` passes `role="fast"` to checkers
- Tests run from `~/.claude` together with every other suite (one invocation since #21), or alone with `python -m pytest agents/clean-code-analyzer/tests`
- Prompts in `scripts/prompts/local/` (6 templates) and `scripts/prompts/claude/` (6 fallback templates)

