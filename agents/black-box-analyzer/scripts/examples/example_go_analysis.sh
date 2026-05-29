#!/usr/bin/env bash
# Example: Analyze a Go project with gin framework

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="${1:-/path/to/go-project}"
OUTPUT_DIR="${2:-./analysis-output}"

echo "🔍 Black-Box Test Analysis for Go Project"
echo "=========================================="
echo ""
echo "Project: $PROJECT_PATH"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Phase 0: Analyze project structure
echo "📊 Phase 0: Analyzing project structure..."
python "$SCRIPT_DIR/../analyze_project_structure.py" \
    "$PROJECT_PATH" \
    --output-format json \
    > "$OUTPUT_DIR/project_info.json"

echo "✅ Project info saved to $OUTPUT_DIR/project_info.json"
echo ""

# Phase 1a: Extract API endpoints
echo "🔍 Phase 1a: Extracting API endpoints..."
python "$SCRIPT_DIR/../extract_api_endpoints.py" \
    "$PROJECT_PATH" \
    --language go \
    --output "$OUTPUT_DIR/endpoints.json"

ENDPOINT_COUNT=$(jq '.endpoint_count' "$OUTPUT_DIR/endpoints.json")
echo "✅ Found $ENDPOINT_COUNT endpoints"
echo ""

# Phase 1b: Parse test files
echo "📝 Phase 1b: Parsing test files..."
python "$SCRIPT_DIR/../parse_test_files.py" \
    "$PROJECT_PATH" \
    --language go \
    --output "$OUTPUT_DIR/tests.json"

TEST_COUNT=$(jq '.test_count' "$OUTPUT_DIR/tests.json")
echo "✅ Found $TEST_COUNT tests"
echo ""

# Phase 2: Calculate input combinations
echo "🔢 Phase 2: Calculating input combinations..."
python "$SCRIPT_DIR/../calculate_input_combinations.py" \
    "$OUTPUT_DIR/endpoints.json" \
    --output "$OUTPUT_DIR/scenarios.json" \
    --verbose

SCENARIO_COUNT=$(jq '.scenario_count' "$OUTPUT_DIR/scenarios.json")
echo "✅ Generated $SCENARIO_COUNT test scenarios"
echo ""

# Phase 3: Generate coverage matrix
echo "📋 Phase 3: Generating coverage matrix..."
python "$SCRIPT_DIR/../generate_coverage_matrix.py" \
    "$OUTPUT_DIR/scenarios.json" \
    "$OUTPUT_DIR/tests.json" \
    --output "$OUTPUT_DIR/coverage_matrix.json" \
    --markdown "$OUTPUT_DIR/coverage_report.md" \
    --summary

COVERAGE_PERCENT=$(jq '.coverage_stats.coverage_percent' "$OUTPUT_DIR/coverage_matrix.json")
echo "✅ Coverage: $COVERAGE_PERCENT%"
echo ""

# Phase 4: Prioritize by risk
echo "🎯 Phase 4: Prioritizing missing tests by risk..."
python "$SCRIPT_DIR/../prioritize_by_risk.py" \
    "$OUTPUT_DIR/coverage_matrix.json" \
    --output "$OUTPUT_DIR/risk_analysis.json" \
    --summary

echo ""
echo "✨ Analysis complete!"
echo ""
echo "📁 Results:"
echo "  - Project info:     $OUTPUT_DIR/project_info.json"
echo "  - Endpoints:        $OUTPUT_DIR/endpoints.json"
echo "  - Tests:            $OUTPUT_DIR/tests.json"
echo "  - Scenarios:        $OUTPUT_DIR/scenarios.json"
echo "  - Coverage matrix:  $OUTPUT_DIR/coverage_matrix.json"
echo "  - Coverage report:  $OUTPUT_DIR/coverage_report.md"
echo "  - Risk analysis:    $OUTPUT_DIR/risk_analysis.json"
echo ""
echo "📊 Summary:"
echo "  - Endpoints:   $ENDPOINT_COUNT"
echo "  - Tests:       $TEST_COUNT"
echo "  - Scenarios:   $SCENARIO_COUNT"
echo "  - Coverage:    $COVERAGE_PERCENT%"
echo ""
echo "🎯 Next steps:"
echo "  1. Review coverage report: less $OUTPUT_DIR/coverage_report.md"
echo "  2. Review risk analysis:   jq '.risk_assessments[:10]' $OUTPUT_DIR/risk_analysis.json"
echo "  3. Implement missing tests based on CRITICAL/HIGH priority gaps"
