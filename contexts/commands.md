# Commands - Meerkat Scripts

Commands for `~/.claude/` scripts and tests.

---

## Security Safety Analyzer (SSA)

### Analyze a project

```bash
cd ~/.claude/agents/security-safety-analyzer/scripts
python orchestrate.py --path /path/to/project
python orchestrate.py --path /path/to/project --full
python orchestrate.py --path /path/to/project --checks security,crypto
python orchestrate.py --path /path/to/project --format table
python orchestrate.py --path /path/to/project --min-severity high --top 20
python orchestrate.py --path /path/to/project --output report.json
python orchestrate.py --path /path/to/project --fast
python orchestrate.py --path /path/to/project --clear-cache
```

**Checkers**: security, crypto, deserialization, misconfiguration, sensitive_data,
crash_bugs, concurrency, resource_leaks, error_handling, prompt_injection

**Flags**:
- (no flags) — incremental: branch-vs-main changed files only
- `--full` — analyze entire repo
- `--since REF` / `--staged` — other incremental sources
- `--min-severity high|medium|low` — filter output
- `--top N` — keep only the N most severe
- `--output FILE` — write JSON to file
- `--fast` / `--role ROLE` — model role override (analyzer, fast, deep, reasoning)
- `--agents N` — N independent local AI calls per file, dedup-merged
- `--no-cache` / `--clear-cache` — per-file content-hash cache control

### SSA tests

```bash
cd ~/.claude/agents/security-safety-analyzer/scripts
python -m pytest tests/unit/ -q
python -m pytest tests/integration/mock/ -q
python -m pytest tests/e2e/ -q
python -m pytest tests/unit/ tests/integration/mock/ tests/e2e/ -q --ignore=tests/integration/mock/test_orchestrate.py   # CI-safe (test_orchestrate.py calls live AI)
python -m pytest tests/integration/real/ -q                          # prompt rendering + live AI
```

---

## Clean Code Analyzer (CCA)

### Analyze a project

```bash
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --full
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --checks solid,dry
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --format table
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --fast
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --role deep
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --no-cache
python ~/.claude/agents/clean-code-analyzer/scripts/orchestrate.py --path /path/to/project --clear-cache
```

**Flags**:
- (no flags) — incremental: branch-vs-main changed files only
- `--full` — analyze entire repo
- `--checks solid,dry` — run specific principles only
- `--fast` — pass `role="fast"` to all semantic checkers (faster, lower quality)
- `--role ROLE` — override model role for semantic checkers (analyzer, fast, deep, reasoning)
- `--no-cache` — bypass the per-file AI result cache
- `--cache-ttl DAYS` / `--clear-cache` — cache expiry / delete all entries
- `--agents N` — N independent local AI calls per file, dedup-merged

**Cache**: raw AI results cached per file in `~/.claude/agents/clean-code-analyzer/.cache`, keyed by content
hash + prompt + role + agent count; files whose AI call failed are never cached. `CCA_CACHE_DIR` overrides the
directory (read when `main()` runs, so subprocess tests can set it).

### CCA tests

```bash
cd ~/.claude/agents/clean-code-analyzer/scripts
python -m pytest tests/unit/ tests/integration/mock/ -q          # CI-safe, incl. golden tests (replayed AI)
python -m pytest tests/e2e/ -q --deselect e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates
python -m pytest tests/integration/real/ -q                      # live AI
```

---

## Golden Fixtures

```bash
# Golden tests (no live AI — recorded responses are replayed)
cd ~/.claude/agents/clean-code-analyzer/scripts && python -m pytest tests/integration/mock/test_golden_projects.py tests/e2e/test_golden_cli.py -q
cd ~/.claude/agents/security-safety-analyzer/scripts && python -m pytest tests/integration/mock/test_golden_projects.py -q
cd ~/.claude/agents/black-box-analyzer && python -m pytest tests/integration/mock/test_golden_projects.py -q

# Regenerate expected files after an intended behavior change, then hand-check every changed record
python ~/.claude/scripts/cli/update_golden.py --agent cca [--project python_project]
python ~/.claude/scripts/cli/update_golden.py --agent ssa
BBA_CACHE_DIR=$(mktemp -d) python ~/.claude/scripts/cli/update_golden.py --agent bba
```

---

## Black-Box Analyzer (BBA)

### Analyze a project

```bash
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project --full
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project --fast
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project --role deep
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project --no-cache
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --path /path/to/project --clear-cache
```

**Flags**:
- (no flags) — incremental: branch-vs-main changed files only
- `--full` — analyze entire repo
- `--fast` — use `fast` model role (lighter, quicker)
- `--role ROLE` — override model role: analyzer, fast, deep, reasoning
- `--agents N` — N independent local AI calls per file, dedup-merged
- `--no-cache` — bypass both caches: per-analyzer `AnalysisResult` cache and per-file local AI cache
- `--clear-cache` — delete cached analysis results + local AI results, then continue the run (`orchestrate.py` exits after clearing; `parallel_analyzer.py` only exits early when no project path is given)

### Test-gap checkers (`--gaps`)

```bash
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --gaps --path /path/to/project
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --gaps --path /path/to/project --full --checks unit,e2e --format table
python ~/.claude/agents/black-box-analyzer/scripts/orchestrate.py --gaps --clear-cache
```

`--gaps` hands every other argument to the shared engine CLI, so the flags are CCA's and SSA's
(`--checks unit,integ_mock,integ_real,e2e`, `--min-severity`, `--top`, `--since`, `--staged`, …), not
the pipeline's. Each tier reports a whole-file "no test file" finding (line 0) for every source file
without a test in that tier, and the AI names the functions that most need one — on those files only.
AI cache: `<BBA cache root>/gaps` (honours `BBA_CACHE_DIR`); the pipeline's `--clear-cache` clears it too.

**Cache**:
- Analysis results cached per `(analyzer, language, source+test file hashes)` in `~/.cache/black-box-analyzer/<project-hash>/result_<Analyzer>.json`
- Invalidation is implicit: any edit to a source or test file changes its hash. Dependency manifests (`go.mod`, `package.json`) are **not** hashed, so a dependency bump alone does not invalidate
- `BBA_CACHE_DIR` overrides the cache root (used by tests to avoid touching the real user cache)
- Report JSON carries a `cache` block: `{"enabled": bool, "hits": int, "misses": int}`

### BBA tests

```bash
cd ~/.claude/agents/black-box-analyzer
python -m pytest tests/unit/ -q
python -m pytest tests/integration/mock/ -q
python -m pytest tests/e2e/ -q
python -m pytest tests/unit/ tests/integration/mock/ -q  # CI-safe (no local AI required)
```

---

## search-tech Skill

```bash
cd ~/.claude/skills/search-tech/scripts
python -m pytest tests/ -q
```

**Cache**: results cached under `~/.cache/search-tech`, keyed by a truncated
sha256 of `(query, filters)`, 1 hour TTL. Entries carry the query and filters
that produced them and are rejected on mismatch. Writes are atomic
(temp file + rename), and a write failure is swallowed so a cache problem never
breaks a search.

In root `testpaths` since #21: its package is `search_tech/`, which collides with nothing.

---

## Language Configuration

`configs/template_languages_config.json` — committed default, 21 languages.
`configs/local_languages_config.json` — auto-copied on first import, gitignored, user-editable.

```python
from lib.config import language_config

language_config.extensions("kotlin")            # ['.kt', '.kts']
language_config.language_for_extension(".tsx")  # 'typescript'
language_config.languages_of_kind("code")       # 15 languages, excludes yaml/sql/dockerfile
language_config.skip_dirs()                     # 19 directories
language_config.extensions_where("has_inheritance")
language_config.standards_for_file(path, content)  # resolves sql/vue dialect from content
language_config.project_indicators()            # ordered {language: [marker files]}, first match wins (BBA project typing)
language_config.language_for_file("Dockerfile")  # 'dockerfile' — by extension, else filename pattern

from lib.engine.discovery import dominant_language, group_by_language, is_test_file
dominant_language(path)                          # code-only vote: language / 'mixed' (<60%) / 'unknown'
dominant_language(path, threshold=0)             # always the leader
group_by_language(files, ("code", "data"))       # {language: [files]}, config order — one checker run each
```

Kinds: `code`, `markup` (vue, razor), `query` (sql), `data` (yaml), `config` (dockerfile), `prompt` (`.prompt`).
A checker opts into non-code kinds with a module-level `FILE_KINDS`. SQL (#42): SSA security, sensitive_data,
misconfiguration, error_handling, concurrency, and CCA comments, naming.

```python
language_config.prompt_language("sql", content)  # 'T-SQL' / 'PostgreSQL' / 'SQL' — what {language} says in a prompt
```

A dialect pattern added to the template does not reach a `local_languages_config.json` written earlier: lists
are replaced, not merged. Re-copy the template if the local file has no edits of its own.

The local file overrides the template field by field. To drop a language locally set
`extensions: []` — deleting its block is not enough, the template puts it back.
Delete `local_languages_config.json` to reset.

---

## Tests

### Run by tier (from ~/.claude/)
```bash
pytest agents/black-box-analyzer/tests/unit/ -v
pytest agents/black-box-analyzer/tests/integration/mock/ -v
pytest agents/black-box-analyzer/tests/integration/real/ -v
pytest agents/black-box-analyzer/tests/e2e/ -v

pytest scripts/cli/tests/units/ -v
pytest scripts/cli/tests/integration-mocks/ -v
pytest scripts/lib/tests/units/ -v
pytest scripts/tests/e2e/ -v
```

### Everything, one invocation (#21)
```bash
cd ~/.claude
python -m pytest -q -m "not integration_reals" \
  --ignore=agents/security-safety-analyzer/scripts/tests/integration/mock/test_orchestrate.py \
  --deselect "agents/clean-code-analyzer/scripts/tests/e2e/test_e2e_full_analysis.py::test_agents_n_completes_without_duplicates"
python -m pytest -q -m integration_reals    # live AI tier
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
python -m py_compile scripts/cli/*.py scripts/lib/*.py
```
