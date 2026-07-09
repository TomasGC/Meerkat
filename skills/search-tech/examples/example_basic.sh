#!/usr/bin/env bash
# Example: Basic technical search usage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$SKILLS_DIR/scripts"

echo "=========================================="
echo "Technical Search - Basic Example"
echo "=========================================="
echo ""

echo "🎯 Purpose: Search for TypeScript async error handling solutions"
echo "📍 Sources: StackOverflow + GitHub Issues"
echo ""

# Search query
QUERY="TypeScript async error handling"

echo "🔍 Searching..."
echo ""

# Run searches in parallel
python "$SCRIPTS_DIR/search_stackoverflow.py" "$QUERY" \
    --tags "typescript,async-await" \
    --min-score 10 \
    --output /tmp/so.json &

python "$SCRIPTS_DIR/search_github.py" "$QUERY" \
    --language typescript \
    --output /tmp/gh.json &

# Wait for both to complete
wait

echo ""
echo "📊 Aggregating results..."
python "$SCRIPTS_DIR/aggregate_results.py" \
    /tmp/so.json /tmp/gh.json \
    --output /tmp/final.json \
    --markdown /tmp/results.md \
    --query "$QUERY"

echo ""
echo "✅ Complete! Results saved to:"
echo "   - JSON: /tmp/final.json"
echo "   - Markdown: /tmp/results.md"
echo ""

# Display markdown results
if [ -f /tmp/results.md ]; then
    cat /tmp/results.md
fi
