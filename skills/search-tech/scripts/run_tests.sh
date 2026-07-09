#!/usr/bin/env bash
# Run all tests for search-tech skill

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "=========================================="
echo "Running search-tech Tests"
echo "=========================================="
echo ""

# Check dependencies
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-cov
fi

# Run tests
echo "🧪 Running unit tests..."
pytest tests/ -v -m "not integration" --cov=. --cov-report=term-missing

echo ""
echo "=========================================="
echo "✅ Tests Complete"
echo "=========================================="
