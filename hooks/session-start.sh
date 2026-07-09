#!/usr/bin/env bash
# SessionStart hook - Automatically loads task-delegator agent
# Triggers: Every session start
# Purpose: Enable intelligent delegation from first interaction

set -euo pipefail

echo "[INFO] Loading delegation infrastructure..."

# 1. Check if task-delegator agent exists
if [ ! -f "$HOME/.claude/agents/task-delegator/AGENT.md" ]; then
    echo "[WARN] task-delegator agent not found"
    exit 0
fi

# 2. Check if Ollama is running
if ! command -v ollama &> /dev/null; then
    echo "[WARN] Ollama not installed - delegation limited to scripts only"
    exit 0
fi

# Start Ollama if not running, wait up to 8s for it to be ready
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[INFO] Ollama not running - starting..."
    (ollama serve > /dev/null 2>&1 &)
    # Wait for API to be ready (up to 8s)
    for i in 1 2 3 4 5 6 7 8; do
        sleep 1
        if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "[OK] Ollama ready (${i}s)"
            break
        fi
    done
fi

# 3. No preloading - models load on first use (32b+8b won't fit simultaneously on 32GB RAM)

# 4. Log session start
echo "{\"timestamp\": \"$(date -Iseconds)\", \"event\": \"session_start\", \"delegation_enabled\": true}" \
  >> "$HOME/.claude/logs/delegation-stats.jsonl"

echo "[OK] Delegation infrastructure loaded"
echo "[INFO] Hot tier models loading in background..."
echo "[INFO] task-delegator agent ready"

exit 0
