# Design Patterns - Meerkat

**Purpose**: Design patterns applied across the Meerkat codebase
**Last Updated**: 2026-10-04

---

## Core Patterns

1. **Strategic Delegation** — mechanical tasks routed to local tools (scripts/local AI/agents), Claude handles only strategic reasoning
2. **Checker Strategy** — CCA (11 checkers), BBA (4 gap checkers) and SSA (10 checkers) share the same `run(path, language, **kwargs) -> dict` interface; orchestrators treat them uniformly
3. **Mechanical vs Semantic Split** — checkers categorized by whether they need a model (AST/grep = mechanical, SOLID/KISS/etc = semantic); different execution paths, same output contract
4. **Async Pipeline** — `asyncio.run(gather(*tasks, return_exceptions=True))` fans out all N file HTTP requests simultaneously; GPU is the only bottleneck
5. **Content-Hash Cache** — model results keyed by `(file, checker, role, content_hash)`, BBA analysis results by `(analyzer, language, all source+test hashes)`; invalidation is implicit (hash changes on file edit), no TTL management required at write time. Known limit: only source/test globs are hashed, so dependency-manifest edits do not invalidate
6. **Branch-vs-Main Incremental** — `git diff base...HEAD --name-only` (three-dot = since merge-base, not since branch creation); avoids false positives when main has moved
7. **Facade Orchestration** — `orchestrate.py` is a pure coordinator: discovers checkers via `importlib`, inspects `run()` signatures via `inspect.signature`, passes only the params each checker declares
10. **Module-level Config Cache (model_config.py, language_config.py)** — no class: each module parses its config once into a module-level `_config` dict on first `_load()` (and at import), so all callers share the same parsed JSON with no repeated file I/O. Tests reset it with `module._config = {}`
11. **Shim / Thin Re-export** — `agents/*/scripts/<pkg>/model_utils.py` re-exports from `scripts/lib/ai/model_utils.py`; agents keep a stable local import path, shared logic lives in one place. Since #21 the shim also binds the agent's own model cache to every `analyze_*` call
8. **Co-located Test Pyramid** — every component keeps its tests in `<component>/tests/{unit,integration_mock,integration_real,e2e}` with data in `tests/fixtures/` (#46); one `conftest.py` per tests tree manages `sys.path`, test files never do
9. **Prompt Template** — `.prompt` files are Python format-string templates (`{code}`, `{language}`, `{file_path}`); validated structurally by unit tests, semantic correctness by integration_real tests
12. **Mechanical-then-AI Reconciliation (SSA)** — a checker's deterministic findings are both rendered into the prompt (`{known_findings}` slot) and used as a ±3-line proximity filter over the AI findings; neither layer needs to know what the other detects
13. **Per-file Prompt Slots** — `analyze_files_parallel(..., extra_slots={path: {...}})` gives each file its own template values, so one prompt template serves N files with N different contexts
14. **Table-driven Rules** — SSA pattern checkers declare `{language: [(regex, message, severity, suggestion)]}` plus a `"*"` bucket for language-agnostic rules; `lib.engine.hybrid` is the only executor, so a new checker is a rule table and a prompt
15. **Env-var Override for Subprocess Test Isolation (BBA)** — `BBA_CACHE_DIR` redirects the cache root and is read lazily on every call, never captured at import. A monkeypatched attribute cannot cross a `subprocess.run` boundary; an inherited env var can, so the same autouse fixture isolates in-process and e2e tests alike
16. **Deterministic Signal over Timing** — cache behaviour is asserted through counters the run reports (`{"enabled", "hits", "misses"}`), not by comparing wall-clock durations between runs, which is flaky under load
17. **Atomic Cache Write** — cache entries are written to a `tempfile.mkstemp` file in the same directory then moved into place with `os.replace`; a crash mid-write leaves the previous entry intact instead of a truncated file. The private writer raises, the public `set()` swallows, so a cache failure never breaks its caller
18. **Self-Verifying Cache Entry** — an entry stores the `query`/`filters` that produced it and `get()` rejects any entry whose stored request differs from the one being served. Cache keys are truncated hashes, so identity cannot be inferred from the filename alone
19. **Detection Reuses Extraction Tables** — a project type is detected with the same `*_PATTERNS` table its analyzer already uses for extraction, filtered by key prefix where a table is shared (`android_*` vs `ios_*`). Detection and extraction cannot drift apart, because adding a rule to a table updates both. Strong signals (file marker, manifest framework) admit a type outright; source patterns need `_MIN_PATTERN_HITS = 2` distinct keys, since single patterns like `def perform(` match ordinary code
20. **Repo-Boundary Guard on Upward Search** — `find_project_root` stops at the first enclosing `.git` instead of climbing to whatever ancestor happens to hold a manifest. Without it a manifest-less directory silently analyses an unrelated parent project
21. **Single Source for Language Knowledge** — nine per-file language tables across CCA, SSA, BBA and `scripts/` collapse into `configs/template_languages_config.json`, read through `language_config.py`. Before, each agent's table covered a different language set, so the three agents disagreed about which files even existed
22. **Explicit Capability Field over Derive-by-Exclusion** — `has_inheritance` and `kind` are declared per language instead of computed as "everything except X". CCA's inheritance scan used to mean "all languages except python/bash/yaml/dockerfile", so any language added to the config later would have been fed to it silently; `kind: code` keeps a yaml- or sql-heavy tree from winning BBA's `detect_language` vote
23. **Template-as-Base Merge** — the local config merges over the template rather than replacing it, so a field added to the template later reaches a local file written before that field existed, and a malformed local file degrades to the template instead of to an empty config. Used by `language_config.py` (#17) and `model_config.py` (#31). Trade-off: a language or model role can be overridden locally but no longer deleted — `extensions: []` is the escape hatch for languages
24. **Probe the Configured Endpoint, Not a CLI** — `check_server_available` GETs `/api/tags` on `local.base_url` instead of shelling out to `ollama list`; a reachable server with no CLI beside it used to report unavailable, and a provider on another host was never seen at all. An untagged config name matches a served tag by `name == model or name.startswith(f"{model}:")`, so `llama3` never matches `llama3-vision`
25. **Extract-Don't-Rewrite (SSA → scripts/lib/engine)** — the shared analysis engine (`finding`, `cache`, `dedup`, `discovery`, `hybrid`, `orchestrator`) is a straight move of SSA's `common/` + `orchestrate.py` into `scripts/lib/engine/`, parameterizing only the fields that actually differed across agent copies (cache dir, checker registry, `max_workers`, display labels). SSA keeps thin shims so its imports and its two test-mocking seams survive unchanged; keeping SSA's 378 CI-safe tests green after every single-module extraction step (not just at the end) is the fidelity proof that no logic moved wrong
26. **Patch Seam Follows the Real Call Site** — a test that patches `module.symbol` is patching a name binding, not the underlying function; when `symbol` moves to a new module, the patch target must move with it or the test silently exercises the real (unpatched) code path. Hit twice extracting the engine: `run_hybrid`'s AI-server check moved from `common.hybrid.check_server_available` to `lib.engine.hybrid.check_server_available` (7 test files, `str.replace`-able since the string is unique per file); `common.file_utils.subprocess.run` needed no test changes at all because re-importing `subprocess` in the shim binds the same stdlib module object the engine module also imports — patching an attribute on a shared module object reaches every importer, patching a re-exported function reference does not
27. **One Driver, Shape Adapters (run_hybrid)** — every checker, whatever its shape, calls `lib.engine.hybrid.run_hybrid`. Its own params say what it is: `mechanical_fn` for a non-regex mechanical layer (AST, external script), `format_ai_violation` for an AI item shape that differs from the default, `prompt=None` for no AI pass. Defaults reproduce the original SSA behaviour exactly, so adding a CCA shape never touched SSA
28. **Never Cache a Failure** — `analyze_files_parallel(failed=set())` collects files whose AI call produced no usable answer (None, unparseable, exception); `run_hybrid` skips caching them. A parsed `[]` is a genuine clean result and is cached. Pre-filling `[]` for every file sent would turn one timeout into 7 days of silent "clean"
29. **Golden Replay at the Model Seam** — golden tests run the whole pipeline (discovery, mechanical scripts, prompt rendering, JSON extraction, formatting, reconciliation, cache, orchestrator) and replace only the model answer, at `call_model_async`. The replay fails loudly on any unmatched call, missing or unused response, because a silent `[]` would let a golden test pass for the wrong reason
30. **Test the Script Contract, Not an Imagined One** — a checker that parses an external script's JSON must be unit-tested with the script's real output shape. KISS read a `line` the complexity script never emitted and YAGNI read `line` where the script emits `line_start`; mocks built from the checker's assumption, not the script's output, hid both. Keep one real-script test per checker (`test_engine_real.py` asserts the YAGNI finding sits on the real `def` line)
31. **Language Vote Counts Code Only** — language detection votes with `kind == "code"` extensions only; json/md/yaml/config files never outvote source. Same rule as #22, applied to `find_unused_code.py`, where a json-heavy folder made YAGNI's mechanical pass silently find nothing. Since #20 there is exactly one vote, `lib.engine.discovery.dominant_language`, used by the engine, BBA and `find_unused_code`
33. **One Run per Language Group (#20)** — the orchestrator never hands a checker a repo-wide language: it groups the target files by each file's own language and calls `run()` once per group the checker accepts (`FILE_KINDS`, default code), then merges the runs. A prompt that used to read "Given this mixed source file" now always names the file's language, and a manifest is analyzed as yaml by the checkers that understand yaml instead of by everyone or no one. The repo-level vote survives only as a report label
34. **A Whole-File Finding Is Not Near Line 1** — line 0 means "about the whole file" ("no unit test file"). Proximity reconciliation treats it as matching only another line-0 finding, so it can never drop an AI finding on lines 1-3. Without the rule, a function defined at the top of an untested file would vanish from the report
35. **Send the AI Only What It Can Judge** — BBA's gap prompts see the source but not the tests, so asking them about a file that has a test produces confident guesses. `run_hybrid(ai_filter=...)` narrows the AI pass to the files the mechanical layer found untested; the mechanical finding is reported either way, so both layers contribute on every run without an either/or fallback
36. **Resolve Prompt Vocabulary at the Last Shared Step (#42)** — the dialect a prompt should name is computed once, in `model_utils`, from the file's own content (`language_config.prompt_language`), not in each checker. Rule tables keep the stable key (`sql`), prompts get the precise word (`T-SQL`); a caller's per-file `language` slot still wins. Every checker that already called the shared client got dialect-aware prompts with no change of its own
38. **One Package per Agent (#21)** — every importable name an agent owns lives under one package named after it (`cca`, `ssa`, `bba`, `search_tech`); entry scripts are wrappers that import it. Five packages named `common`, three `checkers` and three `orchestrate` used to resolve by `sys.path` order, so the suites could not share a process. Rule: a new agent gets its own package, never a generic top-level name
39. **Dependencies Are Passed, Not Discovered (#21)** — the AI client used to enable its cache by importing `common.cache`, so an agent's cache depended on which `common` came first on `sys.path` (CCA had none, SSA's worked through an adapter by accident). Now `analyze_*(cache=...)` takes a `ModelCache`, and each agent's shim passes its own. An import that silently succeeds or fails depending on the environment is a hidden parameter: make it a real one
40. **No Reader, No Metric (#22)** — three `MetricsCollector` copies were kept in sync on paper, but only search-tech's counters were ever shown (`--verbose` summary). The CLI scripts' `track()` calls (39 of them) and BBA's collector were written and discarded at exit. Removing them settled the "reconcile the API" question: the unification problem disappears with the dead code. Before reconciling two implementations, check that both have a consumer
37. **A Safe Twin for Every Pattern Rule** — each SQL rule ships with a negative test written as the parameterized form of the same statement (`sp_executesql @sql, N'@id INT', @id`, `format('%I', …)`, `EXECUTE … USING`). Pattern rules fail by over-matching, and the safe form is the one real code uses most
41. **The Directory Is the Tier (#46)** — a test's tier is the directory right under its `tests/`, and the marker carries the same name, applied by one root-conftest rule. Before, two directory conventions mapped onto marker names matching neither, and 186 tests sat in no tier directory: a marker-selected CI job (`-m unit`) would have skipped them without a word. With no other way to get a tier, the four tier runs are disjoint and add up to the full collection, which is the check that proves it
32. **Priority Lives in an Ordered List, Not in Per-Item Fields** — when "first match wins" matters, store it as a JSON array (`project_indicators: [{language, markers}]`) rather than a field on each language or an object keyed by name. JSON objects are unordered by spec, a per-language field would inherit the language table's unrelated order (it would have flipped a Go+Python project to Python), and the list can name entries the main table must not contain (`solidity` would have entered every agent's file discovery)

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

One importable package per agent (#21), so no two trees share a top-level name:
- `agents/clean-code-analyzer/scripts/cca/` — `orchestrate`, `checkers/`, `model_utils` shim
- `agents/security-safety-analyzer/scripts/ssa/` — `orchestrate`, `checkers/`, shims over lib.engine (`hybrid`, `dedup`, `cache`, `file_utils`), `model_utils`
- `agents/black-box-analyzer/scripts/bba/` — `orchestrate`, `checkers/`, domain modules (`models`, `constants`, `cache`, `utils`), `model_utils`; the pipeline's CLI scripts stay beside it
- `skills/search-tech/scripts/search_tech/` — `SearchCache`, `SearchQuery`/`SearchResult` models, `MetricsCollector` (search counters; logging itself from `lib.logger`), utils (kept apart from `lib`: different code that only shared file names)

The shared library is `scripts/lib/`. `template-base/shared/` is a template directory, not a package.
