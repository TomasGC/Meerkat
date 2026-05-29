#!/usr/bin/env bash
# Example: Analyze Android mobile application
#
# This script demonstrates analyzing an Android app with Kotlin and Jetpack Compose.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$(dirname "$SCRIPT_DIR")/scripts"
FIXTURE_DIR="$(dirname "$SCRIPT_DIR")/tests/fixtures/android_project"

echo "=========================================="
echo "Android Mobile Application Analysis"
echo "=========================================="
echo ""

echo "📱 Project: Android app (Kotlin + Jetpack Compose)"
echo "📍 Path: $FIXTURE_DIR"
echo ""

echo "🔍 Running universal analyzer..."
echo ""

python "$ANALYZER_DIR/parallel_analyzer.py" \
    "$FIXTURE_DIR" \
    --verbose \
    --output android_analysis.json

echo ""
echo "=========================================="
echo "✅ Analysis Complete"
echo "=========================================="
echo ""

echo "📊 Results saved to: android_analysis.json"
echo ""

# Show summary
echo "📋 Summary:"
jq -r '
  "  - Language: \(.project_info.language)",
  "  - Project types: \(.project_info.project_types | join(", "))",
  "  - Entry points: \(.summary.total_entry_points)",
  "  - Scenarios: \(.summary.total_scenarios)",
  "  - Coverage: \(.summary.overall_coverage)%"
' android_analysis.json

echo ""
echo "💡 What was detected:"
echo "  - Activities (MainActivity)"
echo "  - Lifecycle methods (onCreate, onStart, onResume)"
echo "  - UI handlers (onButtonClick)"
echo "  - Jetpack Compose composables (UserScreen)"
echo ""

echo "🧪 Test scenarios generated:"
echo "  - Activity lifecycle transitions"
echo "  - UI interaction handlers"
echo "  - State management scenarios"
echo "  - Edge cases (rapid clicks, state loss)"
echo ""

echo "View full results:"
echo "  cat android_analysis.json | jq"
