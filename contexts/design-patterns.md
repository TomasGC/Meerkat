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
11. **Shim / Thin Re-export** — `agents/*/scripts/common/model_utils.py` re-exports from `scripts/lib/ai/model_utils.py`; agents keep a stable local import path, shared logic lives in one place
8. **Co-located Test Pyramid** — tests live next to source (`agent/tests/unit/`, `agent/tests/integration/mock/`, etc.); each level has its own `conftest.py` managing `sys.path`
9. **Prompt Template** — `.prompt` files are Python format-string templates (`{code}`, `{language}`, `{file_path}`); validated structurally by unit tests, semantic correctness by integration/real tests
12. **Mechanical-then-AI Reconciliation (SSA)** — a checker's deterministic findings are both rendered into the prompt (`{known_findings}` slot) and used as a ±3-line proximity filter over the AI findings; neither layer needs to know what the other detects
13. **Per-file Prompt Slots** — `analyze_files_parallel(..., extra_slots={path: {...}})` gives each file its own template values, so one prompt template serves N files with N different contexts
14. **Table-driven Rules** — SSA pattern checkers declare `{language: [(regex, message, severity, suggestion)]}` plus a `"*"` bucket for language-agnostic rules; `common/hybrid.py` is the only executor, so a new checker is a rule table and a prompt
15. **Env-var Override for Subprocess Test Isolation (BBA)** — `BBA_CACHE_DIR` redirects the cache root and is read lazily on every call, never captured at import. A monkeypatched attribute cannot cross a `subprocess.run` boundary; an inherited env var can, so the same autouse fixture isolates in-process and e2e tests alike
16. **Deterministic Signal over Timing** — cache behaviour is asserted through counters the run reports (`{"enabled", "hits", "misses"}`), not by comparing wall-clock durations between runs, which is flaky under load
17. **Atomic Cache Write** — cache entries are written to a `tempfile.mkstemp` file in the same directory then moved into place with `os.replace`; a crash mid-write leaves the previous entry intact instead of a truncated file. The private writer raises, the public `set()` swallows, so a cache failure never breaks its caller
18. **Self-Verifying Cache Entry** — an entry stores the `query`/`filters` that produced it and `get()` rejects any entry whose stored request differs from the one being served. Cache keys are truncated hashes, so identity cannot be inferred from the filename alone
19. **Detection Reuses Extraction Tables** — a project type is detected with the same `*_PATTERNS` table its analyzer already uses for extraction, filtered by key prefix where a table is shared (`android_*` vs `ios_*`). Detection and extraction cannot drift apart, because adding a rule to a table updates both. Strong signals (file marker, manifest framework) admit a type outright; source patterns need `_MIN_PATTERN_HITS = 2` distinct keys, since single patterns like `def perform(` match ordinary code
20. **Repo-Boundary Guard on Upward Search** — `find_project_root` stops at the first enclosing `.git` instead of climbing to whatever ancestor happens to hold a manifest. Without it a manifest-less directory silently analyses an unrelated parent project
21. **Single Source for Language Knowledge** — nine per-file language tables across CCA, SSA, BBA and `scripts/` collapse into `configs/template_languages_config.json`, read through `language_config.py`. Before, each agent's table covered a different language set, so the three agents disagreed about which files even existed
22. **Explicit Capability Field over Derive-by-Exclusion** — `has_inheritance` and `kind` are declared per language instead of computed as "everything except X". CCA's inheritance scan used to mean "all languages except python/bash/yaml/dockerfile", so any language added to the config later would have been fed to it silently; `kind: code` keeps a yaml- or sql-heavy tree from winning BBA's `detect_language` vote
23. **Template-as-Base Merge** — the local config merges over the template rather than replacing it, so a field added to the template later reaches a local file written before that field existed. Trade-off: a language can be overridden locally but no longer deleted — `extensions: []` is the escape hatch
24. **Probe the Configured Endpoint, Not a CLI** — `check_server_available` GETs `/api/tags` on `local.base_url` instead of shelling out to `ollama list`; a reachable server with no CLI beside it used to report unavailable, and a provider on another host was never seen at all. An untagged config name matches a served tag by `name == model or name.startswith(f"{model}:")`, so `llama3` never matches `llama3-vision`
25. **Extract-Don't-Rewrite (SSA → scripts/lib/engine)** — the shared analysis engine (`finding`, `cache`, `dedup`, `discovery`, `hybrid`, `orchestrator`) is a straight move of SSA's `common/` + `orchestrate.py` into `scripts/lib/engine/`, parameterizing only the fields that actually differed across agent copies (cache dir, checker registry, `max_workers`, display labels). SSA keeps thin shims so its imports and its two test-mocking seams survive unchanged; keeping SSA's 378 CI-safe tests green after every single-module extraction step (not just at the end) is the fidelity proof that no logic moved wrong
26. **Patch Seam Follows the Real Call Site** — a test that patches `module.symbol` is patching a name binding, not the underlying function; when `symbol` moves to a new module, the patch target must move with it or the test silently exercises the real (unpatched) code path. Hit twice extracting the engine: `run_hybrid`'s AI-server check moved from `common.hybrid.check_server_available` to `lib.engine.hybrid.check_server_available` (7 test files, `str.replace`-able since the string is unique per file); `common.file_utils.subprocess.run` needed no test changes at all because re-importing `subprocess` in the shim binds the same stdlib module object the engine module also imports — patching an attribute on a shared module object reaches every importer, patching a re-exported function reference does not

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

Four independent `common/` packages exist (the shared library `scripts/lib/` is deliberately not one of them):
- `agents/black-box-analyzer/scripts/common/` — BBA-specific utilities
- `agents/clean-code-analyzer/scripts/common/` — CCA-specific utilities (model_utils shim, cache, file_utils)
- `agents/security-safety-analyzer/scripts/common/` — SSA-specific utilities (hybrid driver, dedup, model_utils shim, cache, file_utils)
- `skills/search-tech/scripts/common/` — search-tech utilities (cache, logger, models, utils)

**Rule**: never run tests from two different `common/` owners in the same pytest invocation — Python's import cache resolves `common` to whichever is first on `sys.path`. This is why `skills/search-tech` is absent from the root `pytest.ini` `testpaths`: including it would collide with the agents' packages. Its suite is run separately from `skills/search-tech/scripts/`.

`template-base/common/` is a template directory, not a Python package — it holds no `.py` and never enters `sys.path`.
