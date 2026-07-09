#!/usr/bin/env bash
# Real-world example: Search for "async error handling" across all 7 platforms
#
# This demonstrates a complete technical search workflow:
# 1. Query multiple platforms in parallel
# 2. Aggregate and rank results
# 3. Generate both JSON and Markdown output
#
# Usage:
#   bash example_real_search.sh
#   bash example_real_search.sh "your search query"

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$PARENT_DIR/scripts"
OUTPUT_DIR="/tmp/search-tech-results"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Query (default or user-provided)
QUERY="${1:-async error handling typescript}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Technical Search - Real World Example                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Query:${NC} $QUERY"
echo -e "${GREEN}Platforms:${NC} 7 (StackOverflow, GitHub Issues, GitHub Discussions, Reddit, Dev.to, Hashnode, Medium)"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Phase 1: Search all platforms in parallel
echo -e "${YELLOW}Phase 1/3:${NC} Searching all platforms..."
echo ""

echo "  - StackOverflow (REST API)..."
python "$SCRIPTS_DIR/search_stackoverflow.py" "$QUERY" \
    --tags typescript \
    --output "$OUTPUT_DIR/stackoverflow.json" \
    --verbose &

echo "  - GitHub Issues (gh CLI)..."
python "$SCRIPTS_DIR/search_github.py" "$QUERY" \
    --language typescript \
    --output "$OUTPUT_DIR/github.json" \
    --verbose &

echo "  - Reddit (r/programming, r/typescript)..."
python "$SCRIPTS_DIR/search_reddit.py" "$QUERY" \
    --subreddits programming,typescript \
    --output "$OUTPUT_DIR/reddit.json" \
    --verbose &

echo "  - Dev.to (REST API)..."
python "$SCRIPTS_DIR/search_devto.py" "$QUERY" \
    --tags typescript \
    --output "$OUTPUT_DIR/devto.json" \
    --verbose &

echo "  - Hashnode (GraphQL API)..."
python "$SCRIPTS_DIR/search_hashnode.py" "$QUERY" \
    --tags typescript \
    --output "$OUTPUT_DIR/hashnode.json" \
    --verbose &

echo "  - Medium (RSS feeds)..."
python "$SCRIPTS_DIR/search_medium.py" "$QUERY" \
    --tags typescript,javascript \
    --output "$OUTPUT_DIR/medium.json" \
    --verbose &

# Wait for all searches to complete
wait

echo ""
echo -e "${GREEN}✅ All searches completed!${NC}"
echo ""

# Phase 2: Aggregate and rank results
echo -e "${YELLOW}Phase 2/3:${NC} Aggregating results..."
echo ""

python "$SCRIPTS_DIR/aggregate_results.py" \
    "$OUTPUT_DIR/stackoverflow.json" \
    "$OUTPUT_DIR/github.json" \
    "$OUTPUT_DIR/reddit.json" \
    "$OUTPUT_DIR/devto.json" \
    "$OUTPUT_DIR/hashnode.json" \
    "$OUTPUT_DIR/medium.json" \
    --max-results 10 \
    --output "$OUTPUT_DIR/final.json" \
    --markdown "$OUTPUT_DIR/results.md" \
    --query "$QUERY" \
    --verbose

echo ""
echo -e "${GREEN}✅ Aggregation complete!${NC}"
echo ""

# Phase 3: Display results
echo -e "${YELLOW}Phase 3/3:${NC} Results"
echo ""

# Parse JSON to show summary
if command -v jq &> /dev/null; then
    echo -e "${BLUE}Summary:${NC}"
    jq -r '.summary | "  Total results: \(.total_results)\n  Sources: \(.sources | to_entries | map("    - \(.key): \(.value) results") | join("\n"))"' "$OUTPUT_DIR/final.json"
    echo ""

    echo -e "${BLUE}Top 3 Results:${NC}"
    jq -r '.results[:3] | to_entries | map("  \(.key + 1). [\(.value.source)] \(.value.title)\n     Score: \(.value.score) | URL: \(.value.url)") | join("\n\n")' "$OUTPUT_DIR/final.json"
else
    echo -e "${YELLOW}Note:${NC} Install jq for better JSON formatting (optional)"
    echo ""
    echo -e "${BLUE}Results saved to:${NC}"
fi

echo ""
echo -e "${GREEN}Output files:${NC}"
echo "  📄 JSON: $OUTPUT_DIR/final.json"
echo "  📝 Markdown: $OUTPUT_DIR/results.md"
echo ""

# Optional: Open markdown in browser (macOS) or default viewer (Linux)
if command -v open &> /dev/null; then
    echo -e "${BLUE}Opening results in browser...${NC}"
    open "$OUTPUT_DIR/results.md"
elif command -v xdg-open &> /dev/null; then
    echo -e "${BLUE}Opening results in default viewer...${NC}"
    xdg-open "$OUTPUT_DIR/results.md"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Search Complete! ✨                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
