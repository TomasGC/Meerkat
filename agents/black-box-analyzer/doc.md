# black-box-analyzer — Detailed Phase Reference

Operational detail for each analysis phase. AGENT.md has the summary; this has the full manual fallback procedures, language support matrix, output standards, and collaboration patterns.

---

## Phase 0: Project Discovery

**Goal**: Understand project structure, technologies, test frameworks — and determine **project mode**.

**Script**: `analyze_project_structure.py` — auto-detects language, frameworks, endpoint count, test file count. Saves `project_info.json`.

**Mode determination**:
- **0 HTTP endpoints** → LIBRARY/SDK mode → white-box analysis
- **≥1 HTTP endpoints** → API/Web/App mode → black-box analysis
- **Hybrid** → run both pipelines, merge output

**Manual fallback** (no script):
1. Glob key project files (`package.json`, `go.mod`, `Cargo.toml`, `*.csproj`, `pom.xml`, `build.gradle.kts`, `gemspec`)
2. Identify language and frameworks
3. Count HTTP routes/endpoints → determines mode
4. Detect test framework (Jest, xUnit, pytest, JUnit, NUnit, RSpec, etc.)
5. Identify API docs (OpenAPI, Swagger, JSDoc)

---

## Phase 1: Input/Output Enumeration

**Goal**: Identify ALL possible inputs and outputs for each entry point.

### Library Mode

**Script**: `analyze_library_branches.py <src_path> --language auto --output library_methods.json`
- Delegates to Ollama `qwen2.5-coder:7b` via `scripts/prompts/ollama/analyze_library_branches.prompt`
- Extracts: public methods, all branches (null guards, throw conditions, switch/match cases, enum validation, boundary checks, early returns)
- Near-zero Claude tokens

**Manual fallback** (Ollama unavailable → use `scripts/prompts/claude/library_branch_analysis.prompt`):
- For each source file, read public API surface
- For each public method enumerate:
  - Happy path: valid inputs → expected return
  - Null/None/nil inputs for each nullable parameter
  - Empty inputs (empty string, empty array, zero)
  - Boundary values (min, max, -1, 0, MAX_INT)
  - Invalid type/format inputs
  - Each throw/raise/panic condition
  - Each switch/match/when branch

### API/App Mode

**Script**: `extract_api_endpoints.py <project> --output endpoints.json`
- Extracts all endpoints with paths, methods, parameters, response codes, file locations

**Script**: `calculate_input_combinations.py endpoints.json --output scenarios.json`
- Happy path, edge cases (null/empty/max_length/boundary), error scenarios, security scenarios
- Pairwise reduction for large param sets

**Manual fallback**:
1. Parse API contracts (OpenAPI, Swagger)
2. For each endpoint list ALL input params and ALL response codes
3. Generate combinatorial inputs (N booleans → 2^N combos; enum with K values → K combos)
4. Document edge cases: null, empty string, max length, invalid formats

---

## Phase 2: Existing Test Mapping

**Goal**: Map existing tests to input/output scenarios.

**Scripts**:
- `parse_test_files.py <project> --output tests.json [--previous-pass <path>]`
  - Classifies each test as unit/int_mock/int_real/e2e (regex + Ollama fallback via `ollama/infer_test_type.prompt`)
  - With `--previous-pass`: diffs against prior run, reports ONLY newly added tests (60-80% less re-analysis)
- `generate_coverage_matrix.py scenarios.json tests.json --output matrix.json --markdown coverage.md [--mode library]`
  - Produces scenario × test matrix with ✅/❌

**Incremental tracking** — after every pass:
```bash
cp tests.json /path/to/project/.claude/bbanalysis-last-tests.json
```

**Manual fallback**:
1. Find all test files (framework-specific glob: `**/*Test*.cs`, `**/*_test.go`, `**/*.spec.ts`, etc.)
2. For each test extract: tested method/endpoint, inputs, assertions
3. Map to scenarios from Phase 1
4. Calculate coverage %

**Test type decision rules**:
- Single method, no external calls → `[UNIT]`
- Uses mocks/fakes for DB/HTTP/file → `[INT-MOCK]`
- Real file/stream/DB → `[INT-REAL]`
- Full system from entry to output → `[E2E]`

---

## Phase 3: Missing Scenario Identification

**Goal**: ALL untested input/output combos, each tagged with test type.

1. Diff Phase 1 (exhaustive) vs Phase 2 (existing tests)
2. For each gap, classify:
   - **Happy path** — valid inputs, expected success
   - **Edge cases** — boundary values, empty, max
   - **Error cases** — invalid inputs, expected failures
   - **State-dependent** — requires specific preconditions
3. Tag every missing scenario: `[UNIT]` / `[INT-MOCK]` / `[INT-REAL]` / `[E2E]`
4. If incremental: skip scenarios already reported in prior pass

---

## Phase 4: Risk-Based Prioritization

**Script**: `prioritize_by_risk.py matrix.json --output risks.json --summary`

**Manual fallback** (script unavailable → use `scripts/prompts/claude/risk_prioritization.prompt`):

Risk = business_impact × technical_risk × failure_probability (each 1-5):

| Dimension | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| Business impact | payment/auth/billing | admin/config/user writes | user reads | analytics/logs | static/health |
| Technical risk | security vulns | null/missing params/DELETE | validation/error | edge cases | trivial |
| Failure probability | unhandled security / known incident | missing null/param handling | error/edge cases | happy path | trivial |

Levels: CRITICAL ≥ 60 | HIGH 40-59 | MEDIUM 20-39 | LOW < 20

---

## Phase 4b: TDD Refactoring Analysis

**Goal**: Find untestable code patterns; propose minimal refactoring that unlocks new tests.

**Script**: `scan_tdd_refactoring.py <src_path> --language auto --output refactoring.json`
- Delegates to Ollama via `scripts/prompts/ollama/scan_tdd_refactoring.prompt`

**Manual fallback** (Ollama unavailable → use `scripts/prompts/claude/tdd_refactoring_analysis.prompt`):

Anti-patterns to find:
- `static_method_call` — concrete static in testable method (can't mock)
- `new_in_method` — `new ConcreteType()` inside ctor/method (hidden dep)
- `no_interface` — collaborator used widely with no abstraction
- `sealed_or_final` — can't subclass or override in tests
- `global_mutable_state` — static fields cause test pollution
- `hardcoded_io` — baked-in paths/URLs/connection strings force real I/O
- `private_complex_logic` — complex branching unreachable through public surface
- `deep_method_chain` — `a.GetB().GetC().DoD()` — can't intercept
- `thread_sleep_or_datetime_now` — non-injectable time (`DateTime.Now`, `time.Now()`)
- `unhandled_exception_swallow` — empty catch or catch-and-ignore

Output as Table 2 (separate from gap table).

---

## Phase 5: Pattern Analysis

**Goal**: Identify systemic gaps across the codebase.

1. Look for patterns across all endpoints/methods:
   - Validation gaps (all POST endpoints missing null validation)
   - Error handling gaps (no tests for DB failure)
   - Authentication gaps (no expired token tests)
   - State-dependent gaps (no out-of-stock / limit-reached tests)
2. Propose strategic approaches (test template, fixture factory, etc.)
3. Estimate batch effort (N similar tests × 15 min each = X days)

---

## Phase 6: Report Generation

**Goal**: Comprehensive, actionable report with two tables.

1. Report structure:
   - Executive summary (coverage %, critical gap count)
   - **Table 1** — tests writable today (no refactoring required)
   - **Table 2** — tests after refactoring (TDD blockers)
   - Pattern analysis + recommendations
   - Effort estimates
2. Save to `.claude/reports/test-analysis-YYYY-MM-DD.md`
3. Save test inventory to `.claude/bbanalysis-last-tests.json`
4. Create TodoWrite tasks for CRITICAL and HIGH items

---

## Output Standards

### Table 1 — Missing Tests (No Refactoring Required)

```markdown
| # | Method / Endpoint | Scenario | Type | Risk | Priority |
|---|---|---|---|---|---|
| 1 | `GetObject(string)` | null input → ArgumentNullException | [UNIT] | CRITICAL | P1 |
| 2 | `Serialize(obj)` | round-trip with real file stream | [INT-REAL] | MEDIUM | P2 |
```

### Table 2 — Tests Unlocked After Refactoring

```markdown
| # | Blocker | Anti-Pattern | Refactoring | Tests Unlocked | Test Types | Effort |
|---|---|---|---|---|---|---|
| 1 | Static serializer cache | Global mutable state | Add ClearCache() | 2 tests | [UNIT] | Tiny |
| 2 | `new ConcreteSerializer()` in ctor | Hidden dependency | Inject ISerializerFactory | 3 tests | [UNIT][INT-MOCK] | Small |
```

### Full Report Template

```markdown
# Black Box Test Analysis Report
**Project**: [name]
**Date**: [YYYY-MM-DD]
**Mode**: [LIBRARY (white-box) | API/APP (black-box)]
**Analyzed**: [N methods/endpoints / M test files]
**Pass**: [1 (full) | N (incremental — X new gaps since last pass)]

## Executive Summary
- **Total Scenarios**: X
- **Tested Scenarios**: Y (Z%)
- **Missing Scenarios**: W
- **Critical Gaps**: P (Risk ≥ 60)
- **High Risk Gaps**: Q (Risk 40-59)

## Table 1 — Missing Tests (No Refactoring Required)
[table]

### Critical Findings
#### 1. [Method]
- **Missing Test**: [scenario]
- **Test Type**: [UNIT | INT-MOCK | INT-REAL | E2E]
- **Risk Score**: impact × prob = score
- **Reasoning**: [why critical]
- **Recommended Test**: [description]

## Table 2 — Tests Unlocked After Refactoring
[table]

### Refactoring Details
#### 1. [Blocker]
- **Location**: file:line
- **Anti-Pattern**: [description]
- **Proposed Refactoring**: [minimal change]
- **Tests Unlocked**: ...
- **Effort**: Tiny | Small | Medium | Large

## Pattern Analysis
## Recommendations
## Next Steps
```

---

## Multi-Language Support

| Language | Frameworks (API) | Test Frameworks |
|---|---|---|
| Go | gin, echo, fiber, chi, mux | `testing` package |
| TypeScript | Express, NestJS, Fastify | Jest, Vitest, Mocha |
| JavaScript | Express, Fastify | Jest, Mocha |
| C# | ASP.NET (attrs + minimal APIs) | xUnit, NUnit, MSTest |
| Python | FastAPI, Flask, Django | pytest, unittest |
| Java | Spring Boot | JUnit, TestNG |
| Kotlin | Spring Boot (reuses java_ patterns), build.gradle.kts | Kotest |
| PHP | Laravel, Symfony | PHPUnit |
| Rust | (Cargo.toml detection) | cargo-tarpaulin, `#[test]` |
| Swift | Package.swift / .xcodeproj | XCTest |
| C++ | CMakeLists.txt | GTest, Catch2 |
| Ruby | Rails, Sinatra | RSpec, minitest |

---

## Collaboration with Other Agents

- **code-analyzer**: Analyze implementation (when API context needed)
- **Explore**: Search large codebases for specific patterns
- **general-purpose**: Fetch external docs (OpenAPI specs, etc.)

Delegate when: >200 endpoints OR need external API docs OR complex schema parsing (GraphQL).

---

## Performance

- Small (<50 endpoints): 10-20s
- Medium (50-200): 30-60s
- Large (200+): 2-5 min
- `--max-workers 4-8`: 3-5x speedup
