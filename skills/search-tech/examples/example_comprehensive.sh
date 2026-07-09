#!/usr/bin/env bash
# Example: Comprehensive technical search across all 7 platforms

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$SKILLS_DIR/scripts"

echo "=========================================="
echo "Technical Search - Comprehensive Example"
echo "=========================================="
echo ""

echo "🎯 Purpose: Search across ALL platforms for maximum coverage"
echo "📍 Sources: StackOverflow + GitHub (Issues/Discussions) + Reddit + Dev.to + Hashnode + Medium"
echo ""

# Search query
QUERY="react hooks best practices"

echo "🔍 Searching for: $QUERY"
echo ""

# Run all searches in parallel
echo "⚡ Launching parallel searches..."

python "$SCRIPTS_DIR/search_stackoverflow.py" "$QUERY" \
    --tags "react,hooks" \
    --min-score 10 \
    --output /tmp/so.json &

python "$SCRIPTS_DIR/search_github.py" "$QUERY" \
    --language javascript \
    --output /tmp/gh.json &

python "$SCRIPTS_DIR/search_reddit.py" "$QUERY" \
    --subreddits "react,reactjs,learnreact" \
    --output /tmp/reddit.json &

python "$SCRIPTS_DIR/search_devto.py" "$QUERY" \
    --tags "react,javascript" \
    --output /tmp/devto.json &

python "$SCRIPTS_DIR/search_hashnode.py" "$QUERY" \
    --tags "react,javascript" \
    --output /tmp/hashnode.json &

python "$SCRIPTS_DIR/search_medium.py" "$QUERY" \
    --tags "react,javascript,programming" \
    --output /tmp/medium.json &

# Wait for all background jobs
wait

echo ""
echo "📊 Aggregating results from all platforms..."
python "$SCRIPTS_DIR/aggregate_results.py" \
    /tmp/so.json \
    /tmp/gh.json \
    /tmp/reddit.json \
    /tmp/devto.json \
    /tmp/hashnode.json \
    /tmp/medium.json \
    --output /tmp/final.json \
    --markdown /tmp/results.md \
    --query "$QUERY"

echo ""
echo "✅ Complete! Results saved to:"
echo "   - JSON: /tmp/final.json"
echo "   - Markdown: /tmp/results.md"
echo ""

# Display summary
echo "📈 Coverage Summary:"
cat /tmp/final.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
sources = data.get('sources', {})
total = data.get('total_results', 0)
print(f'  Total results: {total}')
for source, count in sources.items():
    print(f'  - {source}: {count}')
"

echo ""
echo "📄 Top Results:"
cat /tmp/results.md
