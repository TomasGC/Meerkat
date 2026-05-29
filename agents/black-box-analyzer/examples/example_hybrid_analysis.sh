#!/usr/bin/env bash
# Example: Analyze hybrid project (Android + REST API)
#
# This script demonstrates analyzing a project with multiple types.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$(dirname "$SCRIPT_DIR")/scripts"
FIXTURE_DIR="$(dirname "$SCRIPT_DIR")/tests/fixtures/hybrid_project"

echo "=========================================="
echo "Hybrid Project Analysis (Android + API)"
echo "=========================================="
echo ""

echo "🔀 Project: Hybrid (Android app + Go API)"
echo "📍 Path: $FIXTURE_DIR"
echo ""

echo "🔍 Running universal analyzer..."
echo ""

python "$ANALYZER_DIR/parallel_analyzer.py" \
    "$FIXTURE_DIR" \
    --verbose \
    --output hybrid_analysis.json

echo ""
echo "=========================================="
echo "✅ Analysis Complete"
echo "=========================================="
echo ""

echo "📊 Results saved to: hybrid_analysis.json"
echo ""

# Show summary
echo "📋 Overall Summary:"
jq -r '
  "  - Project types detected: \(.project_info.project_types | join(", "))",
  "  - Primary type: \(.project_info.primary_type)",
  "  - Total entry points: \(.summary.total_entry_points)",
  "  - Total scenarios: \(.summary.total_scenarios)",
  "  - Overall coverage: \(.summary.overall_coverage)%"
' hybrid_analysis.json

echo ""
echo "📱 Android Component:"
jq -r '
  .results.android_app |
  "  - Entry points: \(.entry_points)",
  "  - Scenarios: \(.scenarios)",
  "  - Coverage: \(.coverage.coverage_percent)%"
' hybrid_analysis.json

echo ""
echo "🌐 API Component:"
jq -r '
  .results.rest_api |
  "  - Entry points: \(.entry_points)",
  "  - Scenarios: \(.scenarios)",
  "  - Coverage: \(.coverage.coverage_percent)%"
' hybrid_analysis.json

echo ""
echo "💡 What was detected:"
echo ""
echo "  Mobile (Android):"
echo "    - MainActivity with lifecycle"
echo "    - API calls to backend"
echo ""
echo "  Backend (Go + Gin):"
echo "    - GET /api/users"
echo "    - GET /api/users/:id"
echo "    - POST /api/users"
echo ""

echo "🧪 Test scenarios generated:"
echo "  - Mobile: Activity lifecycle + UI interactions"
echo "  - API: HTTP request/response scenarios"
echo "  - Integration: Mobile-to-API communication"
echo ""

echo "📊 View results per component:"
echo "  - Android: cat hybrid_analysis.json | jq .results.android_app"
echo "  - API: cat hybrid_analysis.json | jq .results.rest_api"
echo "  - Aggregated: cat hybrid_analysis.json | jq .results.hybrid"
