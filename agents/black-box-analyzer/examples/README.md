# Usage Examples

This directory contains example scripts demonstrating how to use the black-box-analyzer for different project types.

## Available Examples

### 1. CLI Application Analysis
**Script**: `example_cli_analysis.sh`

Analyzes a Go CLI application using Cobra framework.

```bash
cd examples
./example_cli_analysis.sh
```

**Detects**:
- CLI commands and subcommands
- Command-line flags and options
- Flag types and default values

**Generates scenarios for**:
- Valid flag combinations
- Missing required flags
- Invalid flag values
- Command injection attempts

---

### 2. Mobile Application Analysis
**Script**: `example_mobile_analysis.sh`

Analyzes an Android application with Kotlin and Jetpack Compose.

```bash
cd examples
./example_mobile_analysis.sh
```

**Detects**:
- Activities and Fragments
- Lifecycle methods (onCreate, onStart, onResume, etc.)
- UI event handlers (onClick, onLongClick)
- Jetpack Compose composables

**Generates scenarios for**:
- Activity lifecycle transitions
- UI interaction handlers
- State management
- Edge cases (rapid clicks, configuration changes)

---

### 3. Frontend Application Analysis
**Script**: `example_fullstack_analysis.sh`

Analyzes a React frontend application with TypeScript.

```bash
cd examples
./example_fullstack_analysis.sh
```

**Detects**:
- React components (function and arrow components)
- React hooks (useState, useEffect, custom hooks)
- Component props and their types
- React Router routes

**Generates scenarios for**:
- Valid prop combinations
- Missing required props
- Invalid prop types
- Async state updates
- Edge cases (rapid re-renders)

---

### 4. Hybrid Project Analysis
**Script**: `example_hybrid_analysis.sh`

Analyzes a hybrid project containing both Android app and REST API.

```bash
cd examples
./example_hybrid_analysis.sh
```

**Detects**:
- Multiple project types (Android + REST API)
- Android components (Activities, lifecycle)
- API endpoints (GET/POST)

**Generates scenarios for**:
- Mobile: Activity lifecycle + UI interactions
- API: HTTP request/response scenarios
- Integration: Mobile-to-API communication

**Output**: Aggregated results showing coverage for each component type.

---

## Running Examples

### Prerequisites

1. Python 3.12+ installed
2. Dependencies installed:
   ```bash
   pip install -r ../scripts/requirements.txt
   ```

3. Make scripts executable (Unix/Mac):
   ```bash
   chmod +x *.sh
   ```

### Run All Examples

```bash
# From examples directory
for example in example_*.sh; do
    echo "Running $example..."
    ./"$example"
    echo ""
done
```

### View Results

All examples output JSON files:

```bash
# View CLI analysis
cat cli_analysis.json | jq

# View Android analysis
cat android_analysis.json | jq

# View frontend analysis
cat frontend_analysis.json | jq

# View hybrid analysis
cat hybrid_analysis.json | jq
```

### Extract Specific Information

```bash
# Get entry points count
jq '.summary.total_entry_points' cli_analysis.json

# Get coverage percentage
jq '.summary.overall_coverage' android_analysis.json

# List all detected project types
jq '.project_info.project_types[]' hybrid_analysis.json

# Show risk summary
jq '.results.rest_api.risks' hybrid_analysis.json
```

## Output Format

All examples produce JSON output with this structure:

```json
{
  "success": true,
  "project_info": {
    "language": "...",
    "frameworks": [...],
    "project_types": [...],
    "primary_type": "..."
  },
  "results": {
    "<project_type>": {
      "entry_points": <count>,
      "test_cases": <count>,
      "scenarios": <count>,
      "coverage": {
        "total_scenarios": <count>,
        "tested_scenarios": <count>,
        "untested_scenarios": <count>,
        "coverage_percent": <percentage>
      },
      "risks": {
        "total": <count>,
        "by_level": {
          "CRITICAL": <count>,
          "HIGH": <count>,
          "MEDIUM": <count>,
          "LOW": <count>
        }
      }
    }
  },
  "summary": {
    "total_entry_points": <count>,
    "total_scenarios": <count>,
    "total_tests": <count>,
    "overall_coverage": <percentage>,
    "total_risks": <count>
  }
}
```

## Custom Analysis

### Analyze Your Own Project

```bash
# Basic analysis
python ../scripts/parallel_analyzer.py /path/to/your/project --verbose

# With output file
python ../scripts/parallel_analyzer.py /path/to/your/project \
    --output my_analysis.json \
    --verbose

# With more workers for large projects
python ../scripts/parallel_analyzer.py /path/to/your/project \
    --max-workers 8 \
    --verbose
```

### With Cache

```bash
# First run (builds cache)
python ../scripts/parallel_analyzer.py /path/to/project --verbose

# Subsequent runs (uses cache, much faster)
python ../scripts/parallel_analyzer.py /path/to/project --verbose

# Clear cache and re-analyze
python ../scripts/parallel_analyzer.py /path/to/project \
    --clear-cache \
    --verbose
```

## Understanding Results

### Coverage Percentage

```
coverage_percent = (tested_scenarios / total_scenarios) × 100
```

- **≥80%**: Excellent coverage
- **60-79%**: Good coverage
- **40-59%**: Moderate coverage
- **<40%**: Needs improvement

### Risk Levels

- **CRITICAL** (≥60): Must fix immediately
- **HIGH** (≥40): Fix soon
- **MEDIUM** (≥20): Should fix
- **LOW** (<20): Nice to have

Risk score calculation:
```
risk_score = business_impact × technical_risk × failure_probability
```

Where each factor is rated 1-5.

## Troubleshooting

### Script Won't Execute (Unix/Mac)

```bash
chmod +x example_*.sh
```

### Python Not Found

Ensure Python 3.12+ is in PATH:
```bash
python --version  # Should be 3.12+
```

### Missing Dependencies

```bash
cd ../scripts
pip install -r requirements.txt
```

### JSON Parse Error

Install `jq` for JSON processing:
- **macOS**: `brew install jq`
- **Ubuntu**: `apt-get install jq`
- **Windows**: Download from https://stedolan.github.io/jq/

Or view raw JSON:
```bash
cat cli_analysis.json
```

## Next Steps

After running examples:

1. **Review the results** - Check coverage and risk assessments
2. **Identify gaps** - Focus on untested scenarios
3. **Prioritize by risk** - Fix CRITICAL and HIGH risks first
4. **Write tests** - Add tests for missing scenarios
5. **Re-analyze** - Verify improved coverage

## Additional Resources

- **Main README**: `../scripts/README.md`
- **Test Fixtures**: `../tests/fixtures/`
- **E2E Tests**: `../tests/test_universal_detection.py`
- **Agent Documentation**: `../AGENT.md`
