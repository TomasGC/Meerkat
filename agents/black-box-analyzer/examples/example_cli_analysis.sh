#!/usr/bin/env bash
# Example: Analyze CLI application
#
# This script demonstrates analyzing a CLI application built with Cobra (Go).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$(dirname "$SCRIPT_DIR")/scripts"
FIXTURE_DIR="$(dirname "$SCRIPT_DIR")/tests/fixtures/cli_project"

echo "=========================================="
echo "CLI Application Analysis Example"
echo "=========================================="
echo ""

echo "📦 Project: CLI application (Go + Cobra)"
echo "📍 Path: $FIXTURE_DIR"
echo ""

echo "🔍 Running universal analyzer..."
echo ""

python "$ANALYZER_DIR/parallel_analyzer.py" \
    "$FIXTURE_DIR" \
    --verbose \
    --output cli_analysis.json

echo ""
echo "=========================================="
echo "✅ Analysis Complete"
echo "=========================================="
echo ""

echo "📊 Results saved to: cli_analysis.json"
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
' cli_analysis.json

echo ""
echo "💡 What was detected:"
echo "  - CLI commands (deploy, config set)"
echo "  - Command flags (--force, --environment, --key, --value)"
echo "  - Subcommands (config set)"
echo ""

echo "🧪 Test scenarios generated:"
echo "  - Valid flag combinations"
echo "  - Missing required flags"
echo "  - Invalid flag values"
echo "  - Command injection attempts"
echo ""

echo "View full results:"
echo "  cat cli_analysis.json | jq"
