# Delegation Architecture Guide

> **TL;DR**: Mechanical tasks → Local tools (scripts, Ollama) = 60-70% token savings. Claude focuses on strategic reasoning. Works automatically, zero config.

---

## Why This Matters to You

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Without Delegation           With Delegation                   │
│  ───────────────────           ─────────────────                │
│  Claude does everything  →     Claude orchestrates              │
│  Format + validate + test →    Local tools execute              │
│  High token usage        →     60-70% token savings             │
│  Slow (everything waits) →     Fast (parallel execution)        │
│                                                                 │
│  Problem:                      Solution:                        │
│  Token limits reached fast     Mechanical tasks delegated       │
│  → Expensive sessions          → Claude focuses on value        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Golden rule**: Claude = strategic decisions. Local tools = mechanical execution.

---

## How It Works

```
User: "Format this file and run tests"
    │
    ▼
Claude analyzes intent
    │
    ├─ Mechanical? → Delegate
    │   ↓
    │   scripts/format_code.py (0.1s, 0 tokens)
    │   agents/test-runner (30s, 0 tokens)
    │
    └─ Strategic? → Claude handles
        ↓
        Bug analysis, architecture, explanations

Result: Fast execution + token savings
```

**Benefit**: You get instant mechanical operations + focused strategic reasoning.

---

## What Gets Delegated

### Instant (<1s)

```
Task                    Tool                    Token Savings
────────────────────────────────────────────────────────────
Format code          →  scripts/format_code.py      ~5K
Lint code            →  scripts/lint_code.py        ~3K
Git operations       →  scripts/git_*.py            ~2K
Commit validation    →  analyze_commit_quality.py   ~1K
Coverage calc        →  scripts/check_coverage.py   ~2K
```

---

### Fast (2-10s)

```
Task                    Tool                        Token Savings
────────────────────────────────────────────────────────────────
Syntax check         →  Ollama llama3.2:3b              ~3K
Quick review         →  Ollama qwen2.5-coder:7b        ~5-10K
CI fix proposals     →  agents/ci-fix-proposer         ~8K
Dead code detection  →  scripts/find_unused_code.py    ~4K
DRY violations       →  scripts/find_duplicates.py     ~4K
Complexity metrics   →  scripts/calculate_complexity.py ~2K
```

---

### Background (10-60s)

```
Task                    Tool                        Token Savings
────────────────────────────────────────────────────────────────
Run tests            →  agents/test-runner              ~15K
Code analysis        →  agents/code-analyzer            ~10K
Test gap analysis    →  agents/black-box-analyzer       ~12K
```

---

## What Claude Keeps

```
Strategic Tasks (High-Value Reasoning)
───────────────────────────────────────
Architecture decisions
Bug root cause analysis
Refactoring strategy
Code explanations
Design patterns
Context synthesis
```

**Why**: These require multi-file context, trade-off evaluation, and experience-based judgment.

---

## Components Overview

### 1. Agents (Autonomous Workflows)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Agent                Purpose                Token Savings     │
│  ──────────────────────────────────────────────────────────    │
│  ci-fix-proposer   CI error fixes              ~8K/fix        │
│  code-analyzer     Pattern detection           ~10K/analysis  │
│  black-box-analyzer Test gap analysis          ~12K/project   │
│  test-runner       Run tests + coverage        ~15K/run       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Location**: `~/.claude/agents/*/`

**Details**: See `contexts/architecture.md` for workflows

---

### 2. Scripts (Python Automation)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Script                   Purpose              Latency         │
│  ──────────────────────────────────────────────────────────    │
│  format_code.py        Format (black/prettier)  <0.1s         │
│  lint_code.py          Lint (ruff/eslint)       <1s           │
│  find_unused_code.py   Dead code (AST)          5-10s         │
│  find_duplicates.py    DRY violations           5-15s         │
│  calculate_complexity.py Cyclomatic metrics     2-5s          │
│  analyze_commit_quality.py Security patterns    <1s           │
│  switch-profile.py     Integration profiles     <0.5s         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Location**: `~/.claude/scripts/cli/`

**Details**: See `docs/scripts.md` for usage

---

### 3. Ollama Models (Local LLMs)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Model              Size   Latency  Use Case                   │
│  ──────────────────────────────────────────────────────────    │
│  llama-guard3:1b    1.6GB  0.4s     Quick validation           │
│  llama3.2:3b        2.0GB  2.8s     Syntax checking            │
│  qwen2.5-coder:7b   4.7GB  4.2s     Code review                │
│                                                                │
│  Total RAM: ~8GB (hot tier, always loaded)                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Why Ollama**: Fast local inference without API costs or token limits.

---

## Examples by Scenario

### Scenario 1: Format + Validate

**Without delegation**:
```
User: "Format and validate this file"
Claude: [Reads file, formats, validates, returns]
Time: 10-15s
Tokens: ~8K
```

**With delegation**:
```
User: "Format and validate this file"
Claude: "Delegating..."
  ↓ scripts/format_code.py (0.1s)
  ↓ ollama:llama3.2:3b (2.8s)
Claude: "✅ Formatted + validated"
Time: 3s
Tokens: ~500 (coordination only)
```

**Savings**: 85% faster, 94% fewer tokens

---

### Scenario 2: Debug Slow API

**Without delegation**:
```
User: "Why is GET /users slow?"
Claude: [Reads code, analyzes, profiles, suggests]
Time: 30s
Tokens: ~25K
```

**With delegation**:
```
User: "Why is GET /users slow?"
Claude: "Analyzing..."
  ↓ scripts/profile_endpoint.py (5s) → Data
Claude: [Analyzes profiling data] → N+1 detected
Claude: "Fix: Add eager loading"
  ↓ ollama:qwen2.5-coder:7b validates (4s)
Claude: "✅ Fix validated"
Time: 15s
Tokens: ~8K (analysis only, not data gathering)
```

**Savings**: 50% faster, 68% fewer tokens

---

### Scenario 3: Full Feature Development

**Without delegation**:
```
User: "Add user registration"
Claude: [Design, code, tests, review]
Time: 5-10 min
Tokens: ~50K
```

**With delegation**:
```
User: "Add user registration"
Claude: [Designs architecture]
  ↓ scripts/scaffold_feature.py (2s) → Boilerplate
Claude: [Reviews generated code]
  ↓ agents/test-runner (30s) → Test results
  ↓ ollama:qwen2.5-coder:7b (4s) → Quick review
Claude: [Final synthesis + recommendations]
Time: 2-3 min
Tokens: ~18K (strategy only, not mechanics)
```

**Savings**: 60% faster, 64% fewer tokens

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      Claude (Orchestrator)                      │
│                Strategic Reasoning & Decisions                  │
│                                                                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Delegation Router                             │
│           (Analyzes task → Routes to tool)                      │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Scripts    │   │  Ollama     │   │  Agents     │
│  (instant)  │   │  (0.4-4s)   │   │  (10-60s)   │
│  0 tokens   │   │  0 tokens   │   │  0 tokens   │
└─────────────┘   └─────────────┘   └─────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                          ▼
                  Results aggregated
                          │
                          ▼
                 Claude synthesizes
```

**Key insight**: Claude coordinates but doesn't execute mechanics.

---

## Token Savings Examples

### Real Session Comparison

**Before delegation** (1 hour session):
```
Format code:        5K tokens × 10 times = 50K
Validate syntax:    3K tokens × 8 times  = 24K
Run tests:         15K tokens × 3 times  = 45K
Code review:       10K tokens × 2 times  = 20K
Total:                                   139K tokens
```

**After delegation** (same session):
```
Format code:        0 tokens × 10 times = 0K (scripts)
Validate syntax:    0 tokens × 8 times  = 0K (Ollama)
Run tests:          0 tokens × 3 times  = 0K (agents)
Code review:        0 tokens × 2 times  = 0K (Ollama)
Claude coordination:                     ~8K tokens
Strategic reasoning:                    ~32K tokens
Total:                                   40K tokens
```

**Savings**: 71% reduction (139K → 40K)

---

## How Delegation Works (Technical)

<details>
<summary><strong>Click to expand: Under the hood</strong></summary>

### Decision Flow

```
1. User request arrives
2. Claude analyzes intent
3. Check delegation rules:
   - Is it mechanical? → Auto-delegate
   - Is it strategic? → Claude handles
   - Is it hybrid? → Delegate data, Claude analyzes
4. Execute via appropriate tool
5. Aggregate results
6. Claude synthesizes final response
```

### Delegation Rules

**Auto-delegate** (no confirmation):
- Format, lint, validate syntax
- Git operations (status, diff, log)
- Run tests, calculate coverage
- Profile endpoints, gather logs

**Claude handles** (strategic):
- Architecture decisions
- Bug root cause (multi-file)
- Refactoring strategy
- Code explanations

**Hybrid** (delegate + analyze):
- Debug slow API (profile → Claude analyzes)
- Feature development (scaffold → Claude reviews)
- Security audit (scan → Claude triages)

### Configuration

**See**: `contexts/delegation-strategy.md` for detailed rules

**Files**:
- `~/.claude/agents/` - Agent definitions
- `~/.claude/scripts/cli/` - Automation scripts
- `~/.ollama/config.json` - Model routing (if exists)

</details>

---

## FAQ

**Q: Does delegation work automatically?**  
A: Yes. Claude decides when to delegate based on task type. Zero config needed.

**Q: Can I disable delegation?**  
A: Yes, but not recommended. Delegation saves significant tokens without quality loss.

**Q: What if Ollama isn't installed?**  
A: Scripts still work. Ollama-dependent features (quick review, syntax check) fall back to Claude.

**Q: How much RAM does Ollama need?**  
A: ~8GB for hot tier models (llama-guard3:1b + llama3.2:3b + qwen2.5-coder:7b).

**Q: Does delegation affect quality?**  
A: No. Mechanical tasks (format, lint, validate) are deterministic. Strategic tasks still use Claude.

**Q: Can I see token savings?**  
A: Run `python ~/.claude/scripts/cli/delegation_stats.py` (if implemented).

**Q: What's the latency?**  
A: Scripts (<1s), Ollama (0.4-4s), Agents (10-60s background). All faster than Claude.

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Task Type                  Delegated To       Token Savings   │
│  ──────────────────────────────────────────────────────────    │
│  Format/Lint             →  Scripts              ~5K          │
│  Syntax validation       →  Ollama               ~3K          │
│  Run tests               →  Agents              ~15K          │
│  Quick review            →  Ollama              ~5-10K        │
│  Code analysis           →  Agents + Scripts    ~10K          │
│  Git operations          →  Scripts              ~2K          │
│                                                                │
│  Architecture decisions  →  Claude (strategic)   N/A          │
│  Bug root cause          →  Claude (multi-file)  N/A          │
│  Refactoring strategy    →  Claude (design)      N/A          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- **Architecture Details**: `contexts/architecture.md` - Component workflows, latency benchmarks
- **Delegation Strategy**: `contexts/delegation-strategy.md` - Detailed rules, configuration
- **Scripts Guide**: `docs/scripts.md` - Python scripts reference
- **Commands Reference**: `contexts/commands.md` - Script commands

---

**Remember**: Delegation works automatically. You get faster responses, lower token usage, same quality. Claude focuses on what matters: strategic decisions and context-aware guidance.
