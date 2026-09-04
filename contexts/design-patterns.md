# Design Patterns - Meerkat

**Purpose**: Design patterns applied across the Meerkat codebase
**Last Updated**: 2026-09-04

---

## Core Patterns

1. **Strategic Delegation** — mechanical tasks routed to local tools (scripts/Ollama/agents), Claude handles only strategic reasoning
2. **Checker Strategy** — 12 CCA checkers implement the same `run(path, language, **kwargs) -> dict` interface; orchestrator treats them uniformly
3. **Mechanical vs Semantic Split** — checkers categorized by whether they need a model (AST/grep = mechanical, SOLID/KISS/etc = semantic); different execution paths, same output contract
4. **Async Pipeline** — `asyncio.run(gather(*tasks, return_exceptions=True))` fans out all N file HTTP requests simultaneously; GPU is the only bottleneck
5. **Content-Hash Cache** — Ollama results keyed by `(file, checker, model, content_hash)`; invalidation is implicit (hash changes on file edit), no TTL management required at write time
6. **Branch-vs-Main Incremental** — `git diff base...HEAD --name-only` (three-dot = since merge-base, not since branch creation); avoids false positives when main has moved
7. **Facade Orchestration** — `orchestrate.py` is a pure coordinator: discovers checkers via `importlib`, inspects `run()` signatures via `inspect.signature`, passes only the params each checker declares
8. **Co-located Test Pyramid** — tests live next to source (`agent/tests/unit/`, `agent/tests/integration/mock/`, etc.); each level has its own `conftest.py` managing `sys.path`
9. **Prompt Template** — `.prompt` files are Python format-string templates (`{code}`, `{language}`, `{file_path}`); validated structurally by unit tests, semantic correctness by integration/real tests

---

## CCA Checker Contract

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
orchestrate.py args.model
    -> _run_checker(..., model=args.model)
        -> inspect.signature(mod.run).parameters
            -> if "model" in params: kwargs["model"] = model
                -> checker.run(..., model=model)
                    -> analyze_files_parallel(..., model, ...)
                        -> call_ollama_async(prompt, model=model)
```

Mechanical checkers (`check_dry`, `check_error_handling`, etc.) have no `model` param — the override chain short-circuits at the `inspect.signature` check. Zero coupling.

---

## Namespace Isolation

Three independent `common/` packages exist:
- `scripts/common/` — shared CLI utilities
- `agents/black-box-analyzer/scripts/common/` — BBA-specific utilities
- `agents/clean-code-analyzer/scripts/common/` — CCA-specific utilities (ollama_utils, cache, file_utils)

**Rule**: never run tests from two different agents in the same pytest invocation — Python's import cache resolves `common` to whichever is first on `sys.path`.
