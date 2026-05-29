# Delegation Strategy for Token Optimization

**Goal**: Claude orchestrates, local tools execute (minimize tokens)

**Architecture**: User → Claude (decisions) → Local tools (execution)

---

## Delegation Matrix

### ✅ Delegate to LOCAL

| Task Type | Tool | Latency | Optimization |
|-----------|------|---------|--------------|
| **Syntax validation** | llama-guard3:1b | 0.4s | Instant validation |
| **Quick syntax check** | llama3.2:3b | 2.8s | Fast error detection |
| **Code formatting** | scripts/format_code.py | <0.1s | Instant formatting |
| **Linting** | scripts/lint_code.py | <0.1s | Instant style checks |
| **Test execution** | agents/test-runner | 10-60s | Background execution |
| **Git operations** | scripts/git_*.py | <0.1s | Instant git queries |
| **Coverage calc** | scripts/check_coverage.py | <1s | Quick metrics |
| **Quick code review** | qwen2.5-coder:7b | 4.2s | Fast review |
| **CI fix proposals** | agents/ci-fix-proposer + qwen2.5-coder:7b | 5-10s | Automated fixes |
| **Code pattern analysis** | agents/code-analyzer + scripts | 10-30s | Comprehensive analysis |
| **Dead code detection** | scripts/find_unused_code.py | 5-10s | AST-based detection |
| **DRY violation detection** | scripts/find_duplicates.py | 5-15s | Similarity matching |
| **Complexity metrics** | scripts/calculate_complexity.py | 2-5s | Cyclomatic calculation |
| **Commit quality checks** | scripts/analyze_commit_quality.py | <1s | Pattern analysis |
| **Test analysis** | agents/black-box-analyzer (scripts) | 10-60s | Automated test gap detection |

**Benefits**: Mechanical tasks delegated to optimized tools, freeing Claude for strategic reasoning

---

### 🎯 Keep with CLAUDE (high value)

| Task Type | Why Claude | Reasoning Required |
|-----------|-----------|-------------------|
| **Architecture decisions** | Complex reasoning | Multi-constraint optimization |
| **Bug root cause analysis** | Multi-file context | Cross-component understanding |
| **Refactoring strategy** | Design patterns | Trade-off evaluation |
| **Code explanations** | Pedagogical clarity | Context-aware teaching |
| **Context synthesis** | Memory + history | Long-term coherence |

**Focus**: Strategic reasoning, design decisions, and context-aware guidance

---

## Delegation Workflow

```
User request
    ↓
Claude analyzes intent
    ↓
    ├─ Simple/mechanical? → Delegate to local tool
    │   ├─ Script (instant)
    │   ├─ Ollama (0.4-4s)
    │   └─ Agent (background)
    │
    └─ Complex/strategic? → Claude handles
        ├─ Architecture
        ├─ Design decisions
        └─ Explanations
    ↓
Aggregate results
    ↓
Claude synthesizes response
```

---

## Delegation Rules

### AUTO-DELEGATE (no confirmation)

**Format code**:
```
User: "Format this file"
  ↓
Claude: [Delegates to scripts/format_code.py]
  ↓ (0.1s)
Result: "✅ Formatted 150 lines"
```

**Validate syntax**:
```
User: "Check syntax errors"
  ↓
Claude: [Delegates to llama3.2:3b]
  ↓ (2.8s)
Result: "✅ No syntax errors"
```

**Run tests**:
```
User: "Run all tests"
  ↓
Claude: [Delegates to agents/test-runner]
  ↓ (30s background)
Result: "✅ 142/142 tests passed"
```

---

### HYBRID (Claude + local)

**Bug investigation**:
```
User: "Why is this API slow?"
  ↓
Claude:
1. Read code (Claude)
2. Get profiling data (script)
3. Analyze N+1 queries (Claude)
4. Suggest fixes (Claude)
5. Validate fixes (Ollama)
  ↓
Result: Root cause + fix + validation
```

**Approach**: Claude analyzes context, scripts provide data, Claude synthesizes solution
**Benefit**: Focused Claude reasoning with automated data gathering

---

## Configuration Files

### 1. Ollama routing config

**File**: `~/.claude/ollama/config.json`

```json
{
  "enabled_models": [
    "llama-guard3:1b",
    "llama3.2:3b",
    "qwen2.5-coder:7b"
  ],
  
  "routing": {
    "validate_syntax": "llama-guard3:1b",
    "check_errors": "llama3.2:3b",
    "quick_review": "qwen2.5-coder:7b"
  },
  
  "auto_delegate": true,
  "confirm_before_delegate": false
}
```

---

### 2. Task delegation config

**File**: `~/.claude/task-delegation.json`

```json
{
  "auto_delegate": {
    "format": "scripts/format_code.py",
    "lint": "scripts/lint_code.py",
    "validate": "ollama:llama-guard3:1b",
    "syntax_check": "ollama:llama3.2:3b",
    "run_tests": "agents/test-runner",
    "coverage": "scripts/check_coverage.py",
    "quick_review": "ollama:qwen2.5-coder:7b"
  },
  
  "hybrid_tasks": {
    "debug": ["claude:analyze", "scripts:profile", "claude:suggest"],
    "refactor": ["claude:plan", "ollama:validate", "claude:review"],
    "feature": ["claude:design", "scripts:scaffold", "claude:guide"]
  },
  
  "claude_only": [
    "architecture",
    "design_decision",
    "explain_complex",
    "context_synthesis"
  ]
}
```

---

## Architecture Benefits

### Delegation Strategy

**Mechanical tasks** → Local tools (scripts, Ollama):
- Format code: scripts (instant)
- Validate syntax: Ollama (fast)
- Run tests: agent (background)
- Quick reviews: Ollama (parallel)

**Strategic tasks** → Claude (reasoning):
- Bug investigation: Claude analyzes script data
- Explanations: Claude provides context
- Orchestration: Claude coordinates workflow

**Result**: Claude focuses on high-value reasoning while mechanical operations run locally

---

## Usage Examples

### Example 1: Format + Validate

**Without delegation**:
```
User: "Format and validate this file"
Claude: [Reads file, formats, validates]
```

**With delegation**:
```
User: "Format and validate this file"
Claude: "Delegating..."
  ↓ scripts/format_code.py (0.1s)
  ↓ ollama:llama3.2:3b (2.8s)
Claude: "✅ Formatted + validated"
```

**Benefit**: Instant execution with minimal coordination overhead

---

### Example 2: Debug slow API

**Without delegation**:
```
User: "Why is GET /users slow?"
Claude: [Reads code, analyzes, profiles, suggests]
```

**With delegation**:
```
User: "Why is GET /users slow?"
Claude: "Analyzing..."
  ↓ scripts/profile_endpoint.py (5s) → Data
Claude: [Analyzes profiling data] → N+1 query detected
Claude: "Fix: Add eager loading"
  ↓ ollama:qwen2.5-coder:7b validates fix (4s)
Claude: "✅ Fix validated"
```

**Benefit**: Automated profiling + focused analysis on actual bottleneck

---

### Example 3: Full feature workflow

**Without delegation**:
```
User: "Add user registration feature"
Claude: [Design, code, tests, docs]
```

**With delegation**:
```
User: "Add user registration feature"
Claude: [Designs architecture]
  ↓ scripts/scaffold_feature.py (2s) → Generate boilerplate
Claude: [Reviews generated code]
  ↓ agents/test-runner (30s) → Run tests
  ↓ ollama:qwen2.5-coder:7b (4s) → Quick review
Claude: [Final synthesis]
```

**Benefit**: Claude designs, tools execute, Claude validates - optimal division of labor

---

## Monitoring & Optimization

### Track token usage

**File**: `~/.claude/scripts/cli/track_tokens.py`

```python
#!/usr/bin/env python3
"""Track token usage per session."""

# Log format:
# - Session ID
# - Task type
# - Delegated to (Claude/script/Ollama/agent)
# - Tokens used (0 if delegated)
# - Time taken

# Weekly report:
# - Total tokens saved
# - Most common delegations
# - Optimization opportunities
```

---

## Next Steps

1. ✅ Create delegation config files
2. ✅ Create task-delegator agent
3. ✅ Update ~/.claude/settings.json with hooks
4. ✅ Create monitoring dashboard
5. ✅ Test on real workflow

---

**Expected outcome**: Significant optimization through strategic task delegation while maintaining quality
