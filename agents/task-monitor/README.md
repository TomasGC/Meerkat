# Task Monitor Agent

Autonomous agent that monitors background tasks and notifies the caller (Claude or user) when they complete.

**Key innovation**: Uses Ollama for **100% of monitoring** → **0 Claude tokens consumed**.

## Capabilities

### Active Surveillance (Ollama does everything)
- ✅ Polls process status every 5-10s
- ✅ Reads logs in real-time
- ✅ Detects problems **during execution** (not just at the end)
- ✅ Immediate notification if problem detected

### Proactive Problem Detection
- **Empty/unchanged file** for too long → task stalled
- **Exceptions/stack traces** in logs → crash detected
- **Process disappeared** → unexpected termination
- **Error patterns** → build/test failures

### Intelligent Info Collection
When problem detected:
- Extracts relevant log sections (errors + context)
- Identifies affected files (stack traces, test names)
- Captures timestamps and durations
- Gets exit codes and signals

## Installation

### Prerequisites

1. **Ollama** (required):
```bash
# Installation
curl -fsSL https://ollama.ai/install.sh | sh

# Download model
ollama pull qwen2.5-coder:7b
```

2. **psutil** (optional, for better process monitoring):
```bash
pip install psutil
```

## Usage

### Via Claude Code Agent

```python
# Start task in background
python scripts/test.py --unit > test_output.log 2>&1 &
PID=$!

# Spawn monitoring agent
Agent(
    subagent_type="task-monitor",
    description="Monitor unit tests",
    prompt=f"""
    Monitor unit test execution (PID {PID}).
    
    Log: test_output.log
    Expected: ~462 tests, 2-3 minutes
    
    Detect problems:
    - File stalled (no updates >60s)
    - "FAILED" in output
    - Exceptions
    
    Notify immediately when done or if problem detected.
    """
)
```

### Via Direct Script

```bash
# Launch tests
python scripts/test.py --unit > test.log 2>&1 &
PID=$!

# Monitor with Ollama
python ~/.claude/agents/task-monitor/monitor_task.py \
    --pid $PID \
    --log test.log \
    --type test \
    --output test_notification.txt
```

## Examples

### 1. Unit Tests

```python
Agent(
    subagent_type="task-monitor",
    prompt="""
    Monitor: python scripts/test.py --unit
    PID: 12345
    Log: test_output.log
    
    Detect:
    - Stall (no updates >60s)
    - Test failures
    - Exceptions
    
    Report: test counts, failures, error messages
    """
)
```

### 2. Gradle Build

```python
Agent(
    subagent_type="task-monitor",
    prompt="""
    Monitor: ./gradlew assembleDebug
    PID: 12346
    Log: build.log
    
    Detect:
    - BUILD FAILED
    - Compilation errors
    - Dependency issues
    
    Report: error locations, suggestions
    """
)
```

### 3. Long-Running Script

```python
Agent(
    subagent_type="task-monitor",
    prompt="""
    Monitor: python migrate_data.py
    PID: 12347
    Log: migration.log
    
    Detect:
    - Progress stalled (>120s)
    - Database errors
    - Partial failures
    
    Report immediately if problem.
    """
)
```

## Notification Format

Output file: `task_notification.txt` (or custom)

```
✅ Task Monitor Notification
================================

Event: COMPLETED
Task Type: test
Status: SUCCESS
Duration: 142.3s

Summary: All 462 tests passed successfully

Results:
  Total: 462 tests
  Passed: 462 ✅
  Failed: 0 ❌

Log File: test_output.log
Timestamp: 2026-05-27 16:45:23
================================
```

On error:

```
❌ Task Monitor Notification
================================

Event: PROBLEM
Task Type: test
Status: FAILED
Duration: 87.2s

Summary: Detected 3 test failures

Errors:
  - FileBrowserViewModelTest.shouldLoadItems() - AssertionError
  - ZipInspectorTest.shouldHandleUnicode() - NullPointerException
  - ArchiveBrowserTest.shouldPaginate() - TimeoutException

Affected Files:
  - FileBrowserViewModel.kt:156
  - ZipInspector.kt:89
  - ArchiveBrowser.kt:234

Suggestions:
  - Check null safety in ZipInspector
  - Verify pagination logic timeout
  - Review assertion expectations

Log File: test_output.log
Timestamp: 2026-05-27 16:43:11
================================
```

## Detection Patterns

### Tests
- ✅ Success: "BUILD SUCCESSFUL", "X tests completed"
- ❌ Failure: "FAILED", "Exception", "AssertionError"
- ⏸️ Stall: No log updates >60s

### Builds
- ✅ Success: "BUILD SUCCESSFUL"
- ❌ Failure: "BUILD FAILED", "error:", "cannot resolve"
- ⏸️ Stall: No output >120s

### Deployments
- ✅ Success: "deployment complete", "ready"
- ❌ Failure: "deployment failed", "rollback"
- ⏸️ Stall: No progress >180s

## Architecture

```
TaskMonitor (orchestrator)
    ↓
OllamaMonitor (analysis)
    ↓
Ollama API (qwen2.5-coder:7b)
    ↓
Continuous surveillance loop:
  1. Check process running
  2. Read current logs
  3. Detect stall (unchanged file)
  4. Analyze with Ollama
  5. If problem → notify immediately
  6. Otherwise → wait poll_interval (10s)
```

**Claude token consumption**: **0** ✅

## Configuration

### monitor_task.py Parameters

```bash
--pid              # Process ID to monitor
--pattern          # Or regex pattern of process name
--log              # Log file to watch (required)
--type             # Task type: test | build | deploy | generic
--output           # Notification file (default: task_notification.txt)
--interval         # Polling interval in seconds (default: 10)
--stall-threshold  # Stall threshold in seconds (default: 120)
```

### Examples

```bash
# Test with fast polling
python monitor_task.py --pid 12345 --log test.log --type test --interval 5

# Build with long stall threshold
python monitor_task.py --pid 12346 --log build.log --type build --stall-threshold 300

# Pattern-based (no PID)
python monitor_task.py --pattern "gradle.*test" --log test.log --type test
```

## Benefits

✅ **0 Claude tokens** - Ollama does everything
✅ **Proactive detection** - Immediate ping on problem
✅ **Rich context** - Logs, errors, suggestions
✅ **Generic** - Works for tests, builds, scripts, deployments
✅ **Graceful degradation** - Regex fallback if Ollama unavailable

## Limitations

⚠️ **Ollama required** - Without Ollama, falls back to regex (less intelligent)
⚠️ **Polling overhead** - Checks every 10s (configurable)
⚠️ **Log file based** - Requires task to write to a file

## Roadmap

- [ ] Desktop notification support
- [ ] Slack/Discord webhook support
- [ ] Performance metrics (CPU, RAM) during monitoring
- [ ] Real-time web dashboard
- [ ] Parallel monitoring of multiple tasks
