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

# Check if Ollama server is running
if ! ollama ps &> /dev/null; then
    echo "[WARN] Ollama not running - starting..."
    # Don't block on Ollama start, it may take time
    (ollama serve &> /dev/null &)
fi

# 3. Preload hot tier models (background, don't block session)
(
    sleep 2  # Wait for Ollama to start

    # Check which models are already loaded
    LOADED=$(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}' || echo "")

    # Preload hot tier if not already loaded
    for model in llama-guard3:1b llama3.2:3b qwen2.5-coder:7b; do
        if ! echo "$LOADED" | grep -q "$model"; then
            echo "[INFO] Preloading $model..." >&2
            ollama run "$model" "test" &> /dev/null || true
        fi
    done

    echo "[OK] Hot tier models ready" >&2
) &

# 4. Log session start
echo "{\"timestamp\": \"$(date -Iseconds)\", \"event\": \"session_start\", \"delegation_enabled\": true}" \
  >> "$HOME/.claude/logs/delegation-stats.jsonl"

echo "[OK] Delegation infrastructure loaded"
echo "[INFO] Hot tier models loading in background..."
echo "[INFO] task-delegator agent ready"

exit 0
