#!/usr/bin/env bash
# Delegation router hook
# Intercepts tool calls and delegates when possible
# Purpose: Route mechanical tasks to local tools (0 Claude tokens)

set -euo pipefail

TOOL_NAME="$1"
TOOL_ARGS="${2:-}"

# Load delegation rules
RULES_FILE="$HOME/.claude/configs/delegation-rules.json"

if [ ! -f "$RULES_FILE" ]; then
    echo "[WARN] Delegation rules not found"
    exit 0
fi

# Check if tool is delegable
case "$TOOL_NAME" in
    "Bash")
        # Check if it's a git commit
        if echo "$TOOL_ARGS" | grep -q "git commit"; then
            echo "[INFO] Intercepting git commit - running pre-commit validation"

            # Run pre-commit hook
            if [ -f "$HOME/.claude/hooks/pre-commit-validation.sh" ]; then
                bash "$HOME/.claude/hooks/pre-commit-validation.sh" || {
                    echo "[ERROR] Pre-commit validation failed"
                    exit 1
                }
            fi
        fi
        ;;

    "Edit"|"Write")
        # Could intercept to run formatting after file writes
        # For now, just log
        echo "[INFO] File modification detected: $TOOL_NAME"
        ;;
esac

# Log delegation attempt
echo "{\"timestamp\":\"$(date -Iseconds)\",\"tool\":\"$TOOL_NAME\",\"delegated\":true}" \
  >> "$HOME/.claude/logs/delegation-stats.jsonl"

exit 0
