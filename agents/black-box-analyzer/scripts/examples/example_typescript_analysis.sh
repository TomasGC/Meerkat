#!/usr/bin/env bash
# Example: Analyze a TypeScript project with Express/NestJS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="${1:-/path/to/typescript-project}"
OUTPUT_DIR="${2:-./analysis-output}"

echo "🔍 Black-Box Test Analysis for TypeScript Project"
echo "=================================================="
echo ""

# Use parallel analyzer for faster analysis
echo "⚡ Running parallel analysis (4 workers)..."
python "$SCRIPT_DIR/../parallel_analyzer.py" \
    "$PROJECT_PATH" \
    --output "$OUTPUT_DIR/analysis_report.json" \
    --output-dir "$OUTPUT_DIR" \
    --max-workers 4 \
    --verbose

echo ""
echo "✨ Analysis complete!"
echo ""

# Display summary
COVERAGE=$(jq '.coverage_summary.coverage_percent' "$OUTPUT_DIR/analysis_report.json")
CRITICAL_COUNT=$(jq '.risk_summary.by_level.CRITICAL' "$OUTPUT_DIR/analysis_report.json")
HIGH_COUNT=$(jq '.risk_summary.by_level.HIGH' "$OUTPUT_DIR/analysis_report.json")

echo "📊 Summary:"
jq -r '.project_info | "  - Language:    \(.language)\n  - Frameworks:  \(.frameworks | join(", "))\n  - Endpoints:   \(.endpoint_count)\n  - Test files:  \(.test_file_count)"' "$OUTPUT_DIR/analysis_report.json"
echo "  - Coverage:    $COVERAGE%"
echo ""
echo "🎯 Risk Breakdown:"
echo "  - CRITICAL:    $CRITICAL_COUNT"
echo "  - HIGH:        $HIGH_COUNT"
echo ""

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: $CRITICAL_COUNT CRITICAL risk gaps found!"
    echo ""
    echo "Top 5 CRITICAL risks:"
    jq -r '.risk_assessments[:5] | .[] | "  - [\(.risk_level)] \(.gap.scenario.method) \(.gap.scenario.endpoint)\n    \(.reasoning)"' "$OUTPUT_DIR/risks.json"
fi

echo ""
echo "📁 View full reports:"
echo "  - Full analysis:   jq . $OUTPUT_DIR/analysis_report.json"
echo "  - Coverage matrix: cat $OUTPUT_DIR/coverage.md"
echo "  - Risk details:    jq . $OUTPUT_DIR/risks.json"
