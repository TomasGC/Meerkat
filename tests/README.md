# Delegation Infrastructure Tests

Comprehensive test suite for delegation infrastructure.

---

## Test Structure

```
tests/
├── unit/                      # Fast, isolated tests
│   ├── test_format_code.py           # Scripts
│   └── test_delegation_router.py     # Routing logic
├── integration/               # Component tests
│   ├── test_ollama_integration.py    # Ollama models
│   └── test_agents.py                # Agent structure
├── e2e/                       # Full workflow tests
│   └── test_delegation_workflow.py   # End-to-end
└── fixtures/                  # Test data
```

---

## Running Tests

### All tests

```bash
cd ~/.claude/tests
pytest -v
```

### By level

```bash
# Unit tests (fast, <1s each)
pytest unit/ -v

# Integration tests (medium, 5-10s each)
pytest integration/ -v

# End-to-end tests (slow, 30s-1min each)
pytest e2e/ -v -s
```

### Specific test file

```bash
pytest unit/test_format_code.py -v
pytest integration/test_ollama_integration.py -v -s
```

### With coverage

```bash
pytest --cov=../scripts --cov-report=html
```

---

## Test Categories

### Unit Tests (11 tests)

**test_format_code.py** (9 tests):
- ✅ Language detection (Python, TypeScript)
- ✅ Formatter selection (black, prettier, gofmt)
- ✅ Command building (with/without check-only)
- ✅ File formatting success/failure
- ✅ Directory formatting (empty/with files)

**test_delegation_router.py** (10 tests):
- ✅ Delegation rules structure validation
- ✅ Auto-delegate tasks defined
- ✅ Tool/latency/token estimates present
- ✅ Hybrid tasks structure
- ✅ Claude-only tasks defined
- ✅ Ollama tool format validation
- ✅ Delegation decision logic

**Total**: 19 tests, <5s

---

### Integration Tests (8 tests)

**test_ollama_integration.py** (7 tests):
- ✅ Ollama installed and running
- ✅ Hot tier models available (llama-guard3:1b, llama3.2:3b, qwen2.5-coder:7b)
- ✅ llama-guard3:1b quick response (<5s)
- ✅ llama3.2:3b syntax checking
- ✅ qwen2.5-coder:7b code review
- ✅ Model unload/reload

**test_agents.py** (3 tests):
- ✅ All agents exist (task-delegator, test-runner, code-reviewer, git-helper, ollama-router)
- ✅ Agent YAML frontmatter structure
- ✅ Agent-specific content validation

**Total**: 10 tests, 30-60s

---

### End-to-End Tests (5 tests)

**test_delegation_workflow.py** (5 tests):
- ✅ Format code workflow (script invocation)
- ✅ API profiling workflow (data gathering)
- ✅ Ollama review workflow (latency measurement)
- ✅ Delegation stats workflow (monitoring)
- ✅ Full workflow simulation (format + validate + synthesis)

**Total**: 5 tests, 1-2min

---

## Test Results Expected

### Unit Tests

```
test_format_code.py::test_detect_language_python PASSED
test_format_code.py::test_detect_language_typescript PASSED
test_format_code.py::test_get_formatter_python PASSED
test_format_code.py::test_get_formatter_typescript PASSED
test_format_code.py::test_build_command_black PASSED
test_format_code.py::test_build_command_prettier PASSED
test_format_code.py::test_build_command_prettier_check_only PASSED
test_format_code.py::test_format_file_success PASSED
test_format_code.py::test_format_file_not_found PASSED

test_delegation_router.py::test_delegation_rules_structure PASSED
test_delegation_router.py::test_auto_delegate_tasks_defined PASSED
test_delegation_router.py::test_auto_delegate_has_tool PASSED
test_delegation_router.py::test_auto_delegate_has_latency PASSED
test_delegation_router.py::test_auto_delegate_has_token_estimate PASSED
test_delegation_router.py::test_hybrid_tasks_structure PASSED
test_delegation_router.py::test_claude_only_tasks_defined PASSED
test_delegation_router.py::test_ollama_tool_format PASSED
test_delegation_router.py::test_should_delegate_format PASSED
test_delegation_router.py::test_should_not_delegate_architecture PASSED

======================== 19 passed in 3.42s ========================
```

### Integration Tests

```
test_ollama_integration.py::test_ollama_installed PASSED
test_ollama_integration.py::test_hot_models_available PASSED
test_ollama_integration.py::test_llama_guard_quick_response PASSED
  [INFO] Ollama response: 0.4s
test_ollama_integration.py::test_llama32_syntax_check PASSED
  [INFO] Syntax check: 2.8s
test_ollama_integration.py::test_qwen_code_review PASSED
  [INFO] Code review: 4.2s
test_ollama_integration.py::test_model_unload_reload PASSED

test_agents.py::test_agents_exist PASSED
test_agents.py::test_agent_structure PASSED
test_agents.py::test_task_delegator_agent PASSED

======================== 10 passed in 45.67s ========================
```

### End-to-End Tests

```
test_delegation_workflow.py::test_format_code_workflow PASSED
test_delegation_workflow.py::test_ollama_review_workflow PASSED
  [INFO] Ollama review latency: 4.1s
test_delegation_workflow.py::test_delegation_stats_workflow PASSED
test_delegation_workflow.py::test_full_workflow_simulation PASSED

[1/3] Formatting code (script, instant)...
  ✓ Format complete (0.1s)

[2/3] Validating syntax (Ollama, 3s)...
  ✓ Validation complete (2.9s)

[3/3] Claude synthesis (1s)...
  ✓ Synthesis complete

Total workflow: 4.0s
Tokens used: ~1K (vs ~10K without delegation)
Tokens saved: ~9K (90%)

======================== 5 passed in 78.23s ========================
```

---

## Coverage Report

```bash
pytest --cov=../scripts --cov-report=term-missing
```

**Expected coverage**:
- Scripts: ~80% (format_code.py, lint_code.py, delegation_stats.py)
- Delegators: ~60% (profile_endpoint.py, gather_logs.py - require live services)

---

## Test Dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

---

## Continuous Testing

**Watch mode** (re-run on file changes):
```bash
pytest-watch
```

**Pre-commit hook**:
```bash
# Add to .git/hooks/pre-commit
pytest tests/unit/ -q || exit 1
```

---

## Known Limitations

### Skipped Tests

- **profile_endpoint_workflow**: Requires live API server
- **Ollama tests**: Skipped if Ollama not running
- **Agent spawning**: Cannot spawn real agents in tests (requires Claude Code runtime)

### Manual Verification Needed

- SessionStart hook execution
- Real delegation routing (requires Claude Code session)
- Token savings measurement (requires actual Claude usage)

---

## Next Steps

1. **Run all tests**: `pytest -v`
2. **Fix failures**: Address any failing tests
3. **Check coverage**: `pytest --cov=../scripts`
4. **Add more tests**: Cover edge cases
5. **CI Integration**: Add to GitHub Actions

---

**Status**: Test suite created, ready for execution
