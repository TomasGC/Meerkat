# Design Patterns - Meerkat

**Purpose**: Design patterns applied across the Meerkat codebase
**Last Updated**: 2026-09-09

---

## Core Patterns

1. **Strategic Delegation** — mechanical tasks routed to local tools (scripts/local AI/agents), Claude handles only strategic reasoning
2. **Checker Strategy** — CCA (11 checkers), BBA (4 gap checkers) and SSA (10 checkers) share the same `run(path, language, **kwargs) -> dict` interface; orchestrators treat them uniformly
3. **Mechanical vs Semantic Split** — checkers categorized by whether they need a model (AST/grep = mechanical, SOLID/KISS/etc = semantic); different execution paths, same output contract
4. **Async Pipeline** — `asyncio.run(gather(*tasks, return_exceptions=True))` fans out all N file HTTP requests simultaneously; GPU is the only bottleneck
5. **Content-Hash Cache** — model results keyed by `(file, checker, role, content_hash)`, BBA analysis results by `(analyzer, language, all source+test hashes)`; invalidation is implicit (hash changes on file edit), no TTL management required at write time. Known limit: only source/test globs are hashed, so dependency-manifest edits do not invalidate
6. **Branch-vs-Main Incremental** — `git diff base...HEAD --name-only` (three-dot = since merge-base, not since branch creation); avoids false positives when main has moved
7. **Facade Orchestration** — `orchestrate.py` is a pure coordinator: discovers checkers via `importlib`, inspects `run()` signatures via `inspect.signature`, passes only the params each checker declares
10. **Singleton (model_config.py)** — config loaded once per process via class-level `_instance`; all callers share the same parsed JSON with no repeated file I/O
11. **Shim / Thin Re-export** — `agents/*/scripts/common/model_utils.py` re-exports from `scripts/model_utils.py`; agents keep a stable local import path, shared logic lives in one place
8. **Co-located Test Pyramid** — tests live next to source (`agent/tests/unit/`, `agent/tests/integration/mock/`, etc.); each level has its own `conftest.py` managing `sys.path`
9. **Prompt Template** — `.prompt` files are Python format-string templates (`{code}`, `{language}`, `{file_path}`); validated structurally by unit tests, semantic correctness by integration/real tests
12. **Mechanical-then-AI Reconciliation (SSA)** — a checker's deterministic findings are both rendered into the prompt (`{known_findings}` slot) and used as a ±3-line proximity filter over the AI findings; neither layer needs to know what the other detects
13. **Per-file Prompt Slots** — `analyze_files_parallel(..., extra_slots={path: {...}})` gives each file its own template values, so one prompt template serves N files with N different contexts
14. **Table-driven Rules** — SSA pattern checkers declare `{language: [(regex, message, severity, suggestion)]}` plus a `"*"` bucket for language-agnostic rules; `common/hybrid.py` is the only executor, so a new checker is a rule table and a prompt
15. **Env-var Override for Subprocess Test Isolation (BBA)** — `BBA_CACHE_DIR` redirects the cache root and is read lazily on every call, never captured at import. A monkeypatched attribute cannot cross a `subprocess.run` boundary; an inherited env var can, so the same autouse fixture isolates in-process and e2e tests alike
16. **Deterministic Signal over Timing** — cache behaviour is asserted through counters the run reports (`{"enabled", "hits", "misses"}`), not by comparing wall-clock durations between runs, which is flaky under load

---

## Checker Contract (CCA + BBA)

Every checker (mechanical or semantic) returns the same dict schema:

```python
{
    "principle": str,      # e.g. "SOLID", "DRY"
    "success": bool,
    "violations": [
        {
            "principle": str,
            "file": str,      # repo-relative path
            "line": int,
            "severity": "high" | "medium" | "low",
            "message": str,
            "suggestion": str,
        }
    ],
    "files_analyzed": int,
    "duration_ms": int,
    # optional:
    "error": str,          # only when success=False
    "cache_hits": int,
}
```

Orchestrator deduplicates by `(file, line, principle)` before output.

---

## Model Override Chain

```
orchestrate.py args.role
    -> _run_checker(..., role=args.role)
        -> inspect.signature(mod.run).parameters
            -> if "role" in params: kwargs["role"] = role
                -> checker.run(..., role=role)
                    -> analyze_files_parallel(..., role=role, ...)
                        -> call_model_async(prompt, role=role)
                            -> model_config.get_model(role)
```

Mechanical checkers (`check_dry`, `check_error_handling`, etc.) have no `role` param — the override chain short-circuits at the `inspect.signature` check. Zero coupling.

---

## Namespace Isolation

Four independent `common/` packages exist:
- `scripts/common/` — shared CLI utilities
- `agents/black-box-analyzer/scripts/common/` — BBA-specific utilities
- `agents/clean-code-analyzer/scripts/common/` — CCA-specific utilities (model_utils shim, cache, file_utils)
- `agents/security-safety-analyzer/scripts/common/` — SSA-specific utilities (hybrid driver, dedup, model_utils shim, cache, file_utils)

**Rule**: never run tests from two different agents in the same pytest invocation — Python's import cache resolves `common` to whichever is first on `sys.path`.
