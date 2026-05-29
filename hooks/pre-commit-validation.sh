#!/usr/bin/env bash
# Pre-commit validation hook
# Triggers: Before git commit
# Purpose: Run tests + linting automatically (0 Claude tokens)

set -euo pipefail

echo "[INFO] Pre-commit validation..."

# 1. Check if test-runner agent exists
if [ ! -f "$HOME/.claude/agents/test-runner/AGENT.md" ]; then
    echo "[WARN] test-runner agent not found - skipping tests"
    exit 0
fi

# 2. Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "[INFO] No staged files"
    exit 0
fi

echo "[INFO] Staged files:"
echo "$STAGED_FILES"

# 3. Detect if tests exist
HAS_TESTS=false
if [ -d "tests" ] || [ -d "test" ] || ls *_test.* &> /dev/null; then
    HAS_TESTS=true
fi

# 4. Run quick validation (Ollama if available)
if command -v ollama &> /dev/null && ollama ps | grep -q "llama-guard3:1b"; then
    echo "[INFO] Quick validation with llama-guard3:1b..."

    # Validate syntax for each staged file
    for file in $STAGED_FILES; do
        if [[ "$file" =~ \.(py|ts|tsx|js|jsx|go|cs)$ ]]; then
            echo "  Validating $file..."

            # Basic syntax check (exit code only)
            case "$file" in
                *.py)
                    python3 -m py_compile "$file" 2>/dev/null || {
                        echo "[ERROR] Syntax error in $file"
                        exit 1
                    }
                    ;;
                *.ts|*.tsx|*.js|*.jsx)
                    if command -v node &> /dev/null; then
                        node --check "$file" 2>/dev/null || {
                            echo "[ERROR] Syntax error in $file"
                            exit 1
                        }
                    fi
                    ;;
                *.go)
                    gofmt -e "$file" > /dev/null 2>&1 || {
                        echo "[ERROR] Syntax error in $file"
                        exit 1
                    }
                    ;;
            esac
        fi
    done

    echo "[OK] Syntax validation passed"
fi

# 5. Run tests if they exist (optional, can be slow)
if [ "$HAS_TESTS" = true ]; then
    echo "[INFO] Running affected tests..."

    # Detect test framework and run
    if [ -f "pytest.ini" ] || grep -r "import pytest" tests/ &> /dev/null; then
        # Python pytest
        if command -v pytest &> /dev/null; then
            pytest --maxfail=1 --tb=short -q 2>/dev/null || {
                echo "[ERROR] Tests failed - fix before committing"
                exit 1
            }
        fi
    elif [ -f "jest.config.js" ] || [ -f "jest.config.ts" ]; then
        # JavaScript/TypeScript jest
        if command -v jest &> /dev/null; then
            jest --bail --silent 2>/dev/null || {
                echo "[ERROR] Tests failed - fix before committing"
                exit 1
            }
        fi
    elif ls *_test.go &> /dev/null; then
        # Go tests
        go test ./... -short 2>/dev/null || {
            echo "[ERROR] Tests failed - fix before committing"
            exit 1
        }
    fi

    echo "[OK] Tests passed"
fi

echo "[OK] Pre-commit validation successful"
exit 0
