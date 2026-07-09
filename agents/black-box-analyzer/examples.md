# black-box-analyzer — Example Workflows

---

## Example 1: Library/SDK Analysis (C#)

**Request**: "Analyze test coverage for our REST client library"

### Workflow

**Phase 0** — detect structure:
```bash
python analyze_project_structure.py /path/to/RestClient > project_info.json
# → language: C#, endpoints: 0, test_files: 3 → LIBRARY MODE
```

**Phase 1** — extract branches via Ollama:
```bash
python analyze_library_branches.py /path/to/RestClient/src --language csharp --output library_methods.json
# → 14 public methods, 47 branches extracted
```

**Phase 2** — parse existing tests (incremental):
```bash
python parse_test_files.py /path/to/RestClient --output tests.json \
    --previous-pass /path/to/RestClient/.claude/bbanalysis-last-tests.json
# → 8 tests found, diff: 2 new since last pass
```

**Phase 3** — coverage matrix:
```bash
python generate_coverage_matrix.py library_methods.json tests.json \
    --output matrix.json --markdown coverage.md --mode library
# → 47 scenarios, 12 covered (26%)
```

**Phase 4** — risk scores:
```bash
python prioritize_by_risk.py matrix.json --output risks.json --summary
# → 5 CRITICAL, 8 HIGH, 15 MEDIUM, 7 LOW
```

**Phase 4b** — TDD blockers:
```bash
python scan_tdd_refactoring.py /path/to/RestClient/src --language csharp --output refactoring.json
# → 3 blockers found
```

### Output Summary
```
Coverage: 12/47 scenarios (26%)
CRITICAL: 5 gaps | HIGH: 8 gaps | MEDIUM: 15 gaps | LOW: 7 gaps

Table 1 — Top 3 Critical:
1. RestService.Get(null url) → ArgumentNullException [UNIT] CRITICAL P1
2. RestSerializer.Serialize(null obj) → ArgumentNullException [UNIT] CRITICAL P1
3. RestService.Get(valid) → timeout → throws RestException [INT-REAL] CRITICAL P1

Table 2 — TDD Blockers:
1. static _cache field → GlobalMutableState → Add ClearCache() → 2 tests [UNIT] Tiny
2. new HttpClient() in ctor → HiddenDependency → Inject IHttpClientFactory → 4 tests [UNIT][INT-MOCK] Small
```

---

## Example 2: REST API Analysis (90 endpoints)

**Request**: "Analyze test coverage for our e-commerce API"

### Workflow

**Phase 0** — detect structure:
```bash
python analyze_project_structure.py /path/to/ecommerce-api > project_info.json
# → language: TypeScript/Express, endpoints: 90, test_files: 45 → API MODE
```

**Phase 1 + full pipeline** (parallel):
```bash
python parallel_analyzer.py /path/to/ecommerce-api --output analysis.json --max-workers 4 --verbose
# → 90 endpoints × 6 avg scenarios = 540 total
# → 180 existing tests mapped
# → Coverage: 33%
```

### Output Summary
```
Coverage: 180/540 scenarios (33%)
CRITICAL: 15 | HIGH: 45 | MEDIUM: 120 | LOW: 180

Top Critical:
1. POST /api/payments — null cardNumber → 400 [UNIT] CRITICAL (5×5×5=125)
2. POST /api/payments — DB failure → 500 [INT-MOCK] CRITICAL (5×4×3=60)
3. POST /api/auth/login — expired token → 401 [INT-MOCK] CRITICAL (5×4×3=60)

Patterns:
- All POST endpoints missing null validation (30 tests) → 2 days
- No endpoints test DB failures (90 tests) → 1.5 days
- Auth endpoints missing token expiry tests (10 tests) → 0.5 days
```

---

## Example 3: Communication Style

### Progress Updates During Analysis

```
Phase 1/6: Extracting branches for 14 public methods...
  → analyze_library_branches.py running (Ollama qwen2.5-coder:7b)
  → 47 branches extracted across 14 methods
Phase 2/6: Parsing 8 existing test files (incremental — diff against last pass)...
  → 2 new tests since last pass
Phase 3/6: Generating coverage matrix...
  → 47 scenarios, 12 covered (26%), 35 gaps
```

### Severe Finding Report

```
⚠️ Analysis: 74% of methods lack error handling tests. 5 CRITICAL gaps.

Immediate actions:
1. Implement 5 critical tests (estimated 2 hours)
2. Create null-guard test template, apply to all 14 methods (estimated 1 day)

Total effort to address critical gaps: ~10 hours.
```

### Per-Finding Format

```
CRITICAL: RestService.Get — null url parameter
Risk Score: 80 (Impact=5, TechRisk=4, FailureProb=4)
Reasoning: Core HTTP method, null URLs common from upstream callers, throws unhandled.
Test Type: [UNIT]
Recommended: RestService_Get_NullUrl_ThrowsArgumentNullException
Effort: 10 minutes.
```
