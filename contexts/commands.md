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
python -m pytest tests/unit/ tests/integration/mock/ tests/e2e/ -q   # CI-safe (no local AI)
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

## Tests

### Run by tier (from ~/.claude/)
```bash
pytest agents/black-box-analyzer/tests/unit/ -v
pytest agents/black-box-analyzer/tests/integration/mock/ -v
pytest agents/black-box-analyzer/tests/integration/real/ -v
pytest agents/black-box-analyzer/tests/e2e/ -v

pytest scripts/cli/tests/units/ -v
pytest scripts/cli/tests/integration-mocks/ -v
pytest scripts/common/tests/units/ -v
pytest scripts/tests/e2e/ -v
```

### Run by tier (avoid BBA + scripts together — common namespace collision)
```bash
# BBA only
pytest agents/black-box-analyzer/tests/unit/ -v
pytest agents/black-box-analyzer/tests/unit/ agents/black-box-analyzer/tests/integration/mock/ -q

# Scripts only
pytest scripts/tests scripts/cli/tests scripts/common/tests -m units
```

### CI-safe (no local AI required)
```bash
pytest agents/black-box-analyzer/tests/unit/ agents/black-box-analyzer/tests/integration/mock/ -q
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
