---
name: security-safety-analyzer
description: |
  Autonomous security and safety analyzer (ssa). Checks vulnerabilities, cryptographic failures, unsafe deserialization, misconfiguration, sensitive-data exposure, crash bugs, concurrency issues, resource leaks, error handling, and prompt injection. Each checker runs a mechanical pattern pass plus an AI pass, delegating detection to Python scripts and local AI to minimize Claude token usage.

  <example>
  Context: User wants a security review of a project
  user: "Check this project for security vulnerabilities"
  assistant: "I'll use the security-safety-analyzer to run all checkers in parallel"
  <commentary>
  All 10 checkers run in parallel via scripts + local AI. Claude only synthesizes the report. Token saved: 25-40K.
  </commentary>
  </example>

  <example>
  Context: User wants crypto and secrets checks only
  user: "Check for weak crypto and hardcoded secrets in src/"
  assistant: "I'll use security-safety-analyzer with --checks crypto,sensitive_data"
  <commentary>
  Targeted mode. Only the two named checkers run. Token saved: 20-35K.
  </commentary>
  </example>

  <example>
  Context: User asks for a threat model
  user: "What is the threat model for our payment flow?"
  assistant: "This requires strategic reasoning — I'll handle it directly"
  <commentary>
  Threat modeling is a design activity → Claude directly. ssa is for code-level detection only.
  </commentary>
  </example>

tools: Bash, Read, Grep, Glob
model: haiku
color: red
---

# Security Safety Analyzer (SSA)

Autonomous security and safety analysis agent. Runs 10 checkers in parallel to detect vulnerabilities, cryptographic failures, unsafe deserialization, misconfiguration, sensitive-data exposure, crash bugs, concurrency issues, resource leaks, error handling gaps, and prompt injection risks.

## Quick Start

```bash
cd ~/.claude/agents/security-safety-analyzer/scripts
python orchestrate.py --path /project
python orchestrate.py --path /project --full
python orchestrate.py --path /project --checks security,crash_bugs
python orchestrate.py --path /project --format table
python orchestrate.py --path /project --fast
python orchestrate.py --path /project --no-cache
python orchestrate.py --path /project --clear-cache
```

## Checkers

| Key | Principle | Method | What it detects |
|-----|-----------|--------|-----------------|
| `security` | Security | Hybrid | Injection (SQL, command, XSS), path traversal, hardcoded secrets, SSRF, open redirect, ReDoS, mass assignment, JWT verification bypass |
| `crypto` | Crypto | Hybrid | Broken hashes (MD5, SHA-1), obsolete ciphers, ECB mode, weak randomness, disabled TLS validation, non-constant-time secret comparison |
| `deserialization` | Deserialization | Hybrid | Unsafe object graphs (pickle, BinaryFormatter, node-serialize), permissive type binding, XXE / entity expansion |
| `misconfiguration` | Misconfiguration | Hybrid | Debug pages, permissive CORS, insecure cookies, disabled auth, privileged containers, root users, world-writable permissions |
| `sensitive_data` | SensitiveData | Hybrid | Secrets in logs and consoles, stack traces returned to callers, credentials in URLs, shell tracing |
| `crash_bugs` | CrashBug | Hybrid | Null deref, division by zero, out-of-bounds, unchecked parses and casts, type errors |
| `concurrency` | Concurrency | Hybrid | Race conditions, deadlocks, mutable statics, sleep-based ordering, goroutine and WaitGroup misuse |
| `resource_leaks` | ResourceLeak | Hybrid | Undisposed handles, cleanup only on the success path, blocking waits on async work, uncancelled timers |
| `error_handling` | ErrorHandling | Mechanical | Bare `except`, swallowed errors, empty catch blocks, missing nil checks |
| `prompt_injection` | PromptInjection | Hybrid | User input in LLM prompts, indirect injection, system prompt leakage |

**Hybrid** = mechanical pattern/AST pass always runs; the AI layer adds semantic findings when the local AI server is reachable.
**Mechanical** = no model needed; deterministic AST/pattern analysis only.

The mechanical results are injected into the AI prompt (`{known_findings}` slot) and any AI finding landing within three lines of a mechanical one is dropped, so the two layers do not report the same defect twice.

## Language Coverage

Mechanical patterns per checker (the AI layer covers every language it can read):

| Checker | python | typescript / javascript | csharp | go | powershell | bash | yaml | dockerfile | razor |
|---------|:------:|:-----------------------:|:------:|:--:|:----------:|:----:|:----:|:----------:|:-----:|
| `security` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `crypto` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| `deserialization` | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — | — |
| `misconfiguration` | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — |
| `sensitive_data` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `crash_bugs` | ✅ (AST) | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| `concurrency` | ✅ | — | ✅ | ✅ | ✅ | — | — | — | — |
| `resource_leaks` | ✅ | ✅ | ✅ | — | ✅ | — | — | — | — |
| `error_handling` | ✅ (AST) | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| `prompt_injection` | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — |

Gaps are deliberate where a line-based pattern would be too imprecise: Go resource leaks (`defer` placement needs multi-line context) and JavaScript concurrency are left to the AI layer.

## Checker Contract

All checkers implement:
```python
def run(path: Path, language: str, files=None, agents=1, no_cache=False, role="analyzer") -> dict
```

Returns:
```json
{
  "principle": "Security",
  "success": true,
  "violations": [{"principle", "file", "line", "severity", "message", "suggestion"}],
  "files_analyzed": 12,
  "duration_ms": 340
}
```

AI-sourced violations carry a `[TYPE]: description` message prefix; mechanical ones do not.

## Flags

| Flag | Description |
|------|-------------|
| `--checks all` | Run all 10 checkers (default) |
| `--checks security,crash_bugs` | Run specific checkers |
| `--format json\|table` | Output format (default: json) |
| `--output FILE` | Write JSON to file |
| `--full` | Full-repo analysis (bypass branch-vs-main auto-detection) |
| `--since REF` | Incremental: files changed since git ref |
| `--staged` | Incremental: staged files only |
| `--agents N` | N parallel local AI calls per file, dedup-merged |
| `--no-cache` | Bypass per-file content-hash cache |
| `--clear-cache` | Delete all cached results and exit |
| `--role ROLE` | Override model role (analyzer, fast, deep, reasoning) |
| `--fast` | Shorthand for `--role fast` |
| `--min-severity high\|medium\|low` | Filter output by minimum severity |
| `--top N` | Limit output to top N violations |

## Tests

```bash
cd ~/.claude/agents/security-safety-analyzer/scripts
python -m pytest tests/unit/ -q
python -m pytest tests/integration/mock/ -q
python -m pytest tests/unit/ tests/integration/mock/ -q      # CI-safe, no local AI needed
python -m pytest tests/integration/real/ -q                  # prompt rendering + live AI paths
python -m pytest tests/e2e/ -q
```

`tests/integration/real/test_prompt_templates.py` renders every prompt with the slots its caller supplies and needs no server; it exists because a template referencing an unsupplied slot silently yields zero AI findings.

## Directory Structure

```
agents/security-safety-analyzer/
├── AGENT.md                      # This file
└── scripts/
    ├── orchestrate.py            # Main CLI entry point
    ├── checkers/
    │   ├── check_security.py            # Hybrid: grep + AI
    │   ├── check_crypto.py              # Hybrid via common/hybrid.py
    │   ├── check_deserialization.py     # Hybrid via common/hybrid.py
    │   ├── check_misconfiguration.py    # Hybrid via common/hybrid.py
    │   ├── check_sensitive_data.py      # Hybrid via common/hybrid.py
    │   ├── check_resource_leaks.py      # Hybrid via common/hybrid.py
    │   ├── check_crash_bugs.py          # Hybrid: AST + grep + AI
    │   ├── check_concurrency.py         # Hybrid: grep + AI
    │   ├── check_error_handling.py      # Mechanical: AST/grep
    │   └── check_prompt_injection.py    # Hybrid: grep + AI
    ├── common/
    │   ├── hybrid.py            # Shared mechanical-then-AI driver (pattern-table checkers)
    │   ├── dedup.py             # known_findings rendering + proximity dedup
    │   ├── model_utils.py       # Shim → scripts/lib/ai/model_utils.py
    │   ├── cache.py             # SSA-scoped content-hash cache
    │   └── file_utils.py        # File discovery + language detection
    ├── prompts/
    │   └── local/               # Prompt templates (.prompt files, one per AI checker)
    │       ├── security.prompt
    │       ├── crypto.prompt
    │       ├── deserialization.prompt
    │       ├── misconfiguration.prompt
    │       ├── sensitive_data.prompt
    │       ├── resource_leaks.prompt
    │       ├── crash_bugs.prompt
    │       ├── concurrency.prompt
    │       └── prompt_injection.prompt
    └── tests/
        ├── conftest.py
        ├── unit/                # Pure in-process, no I/O
        ├── integration/mock/     # Real filesystem + mocked AI
        ├── integration/real/     # Prompt rendering + live local AI server
        └── e2e/                  # subprocess against real orchestrate.py
```
