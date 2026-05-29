#!/usr/bin/env bash
# Example: Analyze fullstack application with Next.js
#
# This script demonstrates analyzing a fullstack app (API routes + React components).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$(dirname "$SCRIPT_DIR")/scripts"
FIXTURE_DIR="$(dirname "$SCRIPT_DIR")/tests/fixtures/frontend_project"

echo "=========================================="
echo "Fullstack Application Analysis (React)"
echo "=========================================="
echo ""

echo "🌐 Project: React frontend (TypeScript)"
echo "📍 Path: $FIXTURE_DIR"
echo ""

echo "🔍 Running universal analyzer..."
echo ""

python "$ANALYZER_DIR/parallel_analyzer.py" \
    "$FIXTURE_DIR" \
    --verbose \
    --output frontend_analysis.json

echo ""
echo "=========================================="
echo "✅ Analysis Complete"
echo "=========================================="
echo ""

echo "📊 Results saved to: frontend_analysis.json"
echo ""

# Show summary
echo "📋 Summary:"
jq -r '
  "  - Language: \(.project_info.language)",
  "  - Frameworks: \(.project_info.frameworks | join(", "))",
  "  - Project types: \(.project_info.project_types | join(", "))",
  "  - Entry points: \(.summary.total_entry_points)",
  "  - Scenarios: \(.summary.total_scenarios)",
  "  - Coverage: \(.summary.overall_coverage)%"
' frontend_analysis.json

echo ""
echo "💡 What was detected:"
echo "  - React components (UserButton, UserList)"
echo "  - React hooks (useState, useEffect)"
echo "  - Component props (userId, onClick, disabled)"
echo "  - React Router routes"
echo ""

echo "🧪 Test scenarios generated:"
echo "  - Valid prop combinations"
echo "  - Missing required props"
echo "  - Invalid prop types"
echo "  - Edge cases (rapid state updates, async loading)"
echo ""

echo "View full results:"
echo "  cat frontend_analysis.json | jq"
