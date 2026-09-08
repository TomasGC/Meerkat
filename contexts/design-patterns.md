# Design Patterns - Meerkat

**Purpose**: Design patterns applied across the Meerkat codebase
**Last Updated**: 2026-09-04

---

## Core Patterns

1. **Strategic Delegation** — mechanical tasks routed to local tools (scripts/local AI/agents), Claude handles only strategic reasoning
2. **Checker Strategy** — CCA (12 checkers) and BBA (4 gap checkers) share the same `run(path, language, **kwargs) -> dict` interface; orchestrators treat them uniformly
3. **Mechanical vs Semantic Split** — checkers categorized by whether they need a model (AST/grep = mechanical, SOLID/KISS/etc = semantic); different execution paths, same output contract
4. **Async Pipeline** — `asyncio.run(gather(*tasks, return_exceptions=True))` fans out all N file HTTP requests simultaneously; GPU is the only bottleneck
5. **Content-Hash Cache** — model results keyed by `(file, checker, role, content_hash)`; invalidation is implicit (hash changes on file edit), no TTL management required at write time
6. **Branch-vs-Main Incremental** — `git diff base...HEAD --name-only` (three-dot = since merge-base, not since branch creation); avoids false positives when main has moved
7. **Facade Orchestration** — `orchestrate.py` is a pure coordinator: discovers checkers via `importlib`, inspects `run()` signatures via `inspect.signature`, passes only the params each checker declares
10. **Singleton (model_config.py)** — config loaded once per process via class-level `_instance`; all callers share the same parsed JSON with no repeated file I/O
11. **Shim / Thin Re-export** — `agents/*/scripts/common/model_utils.py` re-exports from `scripts/model_utils.py`; agents keep a stable local import path, shared logic lives in one place
8. **Co-located Test Pyramid** — tests live next to source (`agent/tests/unit/`, `agent/tests/integration/mock/`, etc.); each level has its own `conftest.py` managing `sys.path`
9. **Prompt Template** — `.prompt` files are Python format-string templates (`{code}`, `{language}`, `{file_path}`); validated structurally by unit tests, semantic correctness by integration/real tests

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

Three independent `common/` packages exist:
- `scripts/common/` — shared CLI utilities
- `agents/black-box-analyzer/scripts/common/` — BBA-specific utilities
- `agents/clean-code-analyzer/scripts/common/` — CCA-specific utilities (model_utils shim, cache, file_utils)

**Rule**: never run tests from two different agents in the same pytest invocation — Python's import cache resolves `common` to whichever is first on `sys.path`.
