#!/usr/bin/env python3
"""Generate .github/workflows/coverage.yml tailored to the project.

Reads project_info.json (from analyze_project_structure.py) and emits:
  - .github/workflows/coverage.yml  — parallel tier matrix + Codecov upload
  - Makefile target (or npm/gradle script) for local ReportGenerator run

Usage:
    python generate_ci_workflow.py project_info.json
    python generate_ci_workflow.py project_info.json --output .github/workflows/coverage.yml
    python generate_ci_workflow.py project_info.json --dry-run   # print to stdout
    python generate_ci_workflow.py /path/to/project              # auto-detect project_info
"""

import argparse
import io
import json
import sys
from pathlib import Path
from textwrap import dedent

# Ensure stdout can handle UTF-8 on Windows (cp1252 default breaks YAML output)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from common.models import Language, TestFramework
from common.utils import read_json

# -- Language → GitHub Actions setup step ------------------------------------─

_SETUP_STEPS = {
    Language.PYTHON: """\
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest pytest-cov""",

    Language.TYPESCRIPT: """\
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
      - run: npm ci""",

    Language.JAVASCRIPT: """\
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
      - run: npm ci""",

    Language.GO: """\
      - uses: actions/setup-go@v5
        with:
          go-version: "1.23"
          cache: true""",

    Language.CSHARP: """\
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "9.0.x"
      - run: dotnet tool install --global dotnet-reportgenerator-globaltool
      - run: dotnet restore""",

    Language.JAVA: """\
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: gradle""",

    Language.KOTLIN: """\
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: gradle""",

    Language.RUST: """\
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo install cargo-tarpaulin --locked""",

    Language.SWIFT: """\
      - uses: swift-actions/setup-swift@v2
        with:
          swift-version: "5.10\"""",
}

# -- Language → collect command ------------------------------------------------

_COLLECT_CMD = {
    Language.PYTHON:     "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.TYPESCRIPT: "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.JAVASCRIPT: "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.GO:         "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.CSHARP:     "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.JAVA:       "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.KOTLIN:     "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.RUST:       "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
    Language.SWIFT:      "python scripts/collect_runtime_coverage.py . --tiers ${{ matrix.tier }} --output manifest.json",
}

# -- Language → ReportGenerator input format ----------------------------------

_REPORT_FORMAT = {
    Language.PYTHON:     "lcov",
    Language.TYPESCRIPT: "lcov",
    Language.JAVASCRIPT: "lcov",
    Language.GO:         "lcov",
    Language.CSHARP:     "lcov",
    Language.JAVA:       "lcov",
    Language.KOTLIN:     "lcov",
    Language.RUST:       "lcov",
}

# -- Language → local coverage command (for Makefile / npm script) ------------─

_LOCAL_CMD = {
    Language.PYTHON: "python -m pytest -m {tier} --cov=. --cov-report lcov:.coverage-tiers/coverage_{tier}.lcov -q",
    Language.TYPESCRIPT: "npx jest --testPathPattern={tier} --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/{tier}",
    Language.JAVASCRIPT: "npx jest --testPathPattern={tier} --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/{tier}",
    Language.GO: "go test -tags={tier} -coverprofile=.coverage-tiers/coverage_{tier}.out ./... && gcov2lcov -infile .coverage-tiers/coverage_{tier}.out -outfile .coverage-tiers/coverage_{tier}.lcov",
    Language.CSHARP: "dotnet test --filter Category={tier} --collect:\"XPlat Code Coverage\" --results-directory .coverage-tiers/{tier}",
    Language.JAVA: "./gradlew test -Ptest.groups={tier} jacocoTestReport",
    Language.KOTLIN: "./gradlew test -Ptest.groups={tier} jacocoTestReport",
    Language.RUST: "cargo tarpaulin --features test_{tier} --out Lcov --output-dir .coverage-tiers",
    Language.SWIFT: "xcodebuild test -scheme {tier} -resultBundlePath .coverage-tiers/{tier}.xcresult",
}


def _detect_reportgenerator_install(language: Language) -> str:
    """Return the appropriate ReportGenerator install command."""
    if language == Language.CSHARP:
        return ""  # already installed in setup steps
    return "dotnet tool install --global dotnet-reportgenerator-globaltool 2>/dev/null || true"


def generate_workflow(
    language: Language,
    frameworks: list[str],
    test_framework: TestFramework,
    project_name: str = "project",
) -> str:
    setup = _SETUP_STEPS.get(language, "      - run: echo 'No setup needed'")
    collect_cmd = _COLLECT_CMD.get(language, "echo 'Unsupported language'")
    rg_install = _detect_reportgenerator_install(language)

    # Extra Python dep for the analyzer scripts themselves
    py_setup = ""
    if language != Language.PYTHON:
        py_setup = """\
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install --quiet pytest pytest-cov  # for collect_runtime_coverage.py
"""

    workflow = f"""\
# Auto-generated by black-box-analyzer generate_ci_workflow.py
# Runs test tiers in parallel, uploads per-flag coverage to Codecov.
# Local equivalent: make coverage  (see Makefile target below)

name: Coverage

on:
  push:
    branches: ["main", "master", "develop"]
  pull_request:
    branches: ["main", "master", "develop"]

concurrency:
  group: coverage-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  coverage:
    name: Coverage (${{{{ matrix.tier }}}})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        tier: [unit, int_mock, int_real, e2e]

    steps:
      - uses: actions/checkout@v4

      # -- Language setup ------------------------------------------------------
{setup}

{py_setup}      # -- Collect coverage for this tier ------------------------------------─
      - name: Collect ${{{{ matrix.tier }}}} coverage
        run: {collect_cmd}

      # -- Upload to Codecov with tier flag ------------------------------------
      - uses: codecov/codecov-action@v4
        with:
          files: .coverage-tiers/coverage_${{{{ matrix.tier }}}}.lcov
          flags: ${{{{ matrix.tier }}}}
          name: coverage-${{{{ matrix.tier }}}}
          fail_ci_if_error: false
          token: ${{{{ secrets.CODECOV_TOKEN }}}}

      # -- Store lcov for merge job --------------------------------------------─
      - uses: actions/upload-artifact@v4
        with:
          name: lcov-${{{{ matrix.tier }}}}
          path: .coverage-tiers/coverage_${{{{ matrix.tier }}}}.lcov
          if-no-files-found: warn

  # -- Merge all tiers and upload combined --------------------------------------
  coverage-combined:
    name: Coverage (combined)
    runs-on: ubuntu-latest
    needs: coverage

    steps:
      - uses: actions/checkout@v4

      - name: Download all lcov artifacts
        uses: actions/download-artifact@v4
        with:
          pattern: lcov-*
          path: .coverage-tiers
          merge-multiple: true

      - name: Install lcov
        run: sudo apt-get install -y lcov

      - name: Merge tier coverage files
        run: |
          lcov \\
            --add-tracefile .coverage-tiers/coverage_unit.lcov \\
            --add-tracefile .coverage-tiers/coverage_int_mock.lcov \\
            --add-tracefile .coverage-tiers/coverage_int_real.lcov \\
            --add-tracefile .coverage-tiers/coverage_e2e.lcov \\
            --output-file .coverage-tiers/combined.lcov \\
            --ignore-errors empty

      - uses: codecov/codecov-action@v4
        with:
          files: .coverage-tiers/combined.lcov
          flags: combined
          name: coverage-combined
          fail_ci_if_error: false
          token: ${{{{ secrets.CODECOV_TOKEN }}}}

      - name: Install ReportGenerator
        run: {rg_install if rg_install else "echo 'ReportGenerator already installed'"}

      - name: Generate HTML report
        run: |
          reportgenerator \\
            -reports:".coverage-tiers/*.lcov" \\
            -targetdir:coverage-report \\
            -reporttypes:"Html;Badges;JsonSummary" \\
            -title:"{project_name} Coverage"

      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report-html
          path: coverage-report/
"""
    return workflow


def generate_makefile_target(language: Language) -> str:
    """Generate Makefile coverage target for local use."""
    tiers = ["unit", "int_mock", "int_real", "e2e"]
    local_cmd = _LOCAL_CMD.get(language)

    collect_lines = []
    if local_cmd:
        for tier in tiers:
            collect_lines.append(f"\t{local_cmd.format(tier=tier)}")
    else:
        collect_lines.append("\tpython scripts/collect_runtime_coverage.py . --output manifest.json")

    collect_block = "\n".join(collect_lines)

    return f"""\
# Coverage targets (auto-generated by black-box-analyzer)
.PHONY: coverage coverage-report coverage-open

coverage:
{collect_block}

coverage-report: coverage
\t@command -v reportgenerator >/dev/null 2>&1 || dotnet tool install --global dotnet-reportgenerator-globaltool
\treportgenerator \\
\t\t-reports:".coverage-tiers/*.lcov" \\
\t\t-targetdir:coverage-report \\
\t\t-reporttypes:"Html;Badges;JsonSummary"

coverage-open: coverage-report
\tpython scripts/open_report.py . --skip-collect --skip-merge
"""


def generate_npm_scripts(language: Language) -> str:
    """Generate package.json script entries for JS/TS projects."""
    if language not in (Language.TYPESCRIPT, Language.JAVASCRIPT):
        return ""

    return dedent("""\
        // Add to package.json "scripts" section:
        "coverage:unit":    "jest --testPathPattern=unit --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/unit",
        "coverage:intmock": "jest --testPathPattern=integration --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/int_mock",
        "coverage:intreal": "jest --testPathPattern=int_real --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/int_real",
        "coverage:e2e":     "jest --testPathPattern=e2e --coverage --coverageReporters lcov --coverageDirectory .coverage-tiers/e2e",
        "coverage:report":  "reportgenerator -reports:.coverage-tiers/*/lcov.info -targetdir:coverage-report -reporttypes:Html",
        "coverage:open":    "python scripts/open_report.py . --skip-collect --skip-merge"
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Generate .github/workflows/coverage.yml for the project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_ci_workflow.py project_info.json
  python generate_ci_workflow.py project_info.json --output .github/workflows/coverage.yml
  python generate_ci_workflow.py /path/to/project
  python generate_ci_workflow.py project_info.json --dry-run
        """,
    )
    parser.add_argument(
        "source",
        type=Path,
        help="project_info.json file or project directory (auto-detects project_info.json)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for workflow YAML (default: stdout)",
    )
    parser.add_argument(
        "--makefile",
        type=Path,
        default=None,
        help="Append Makefile coverage targets to this file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated files without writing",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="Project name for report title",
    )
    args = parser.parse_args()

    # Resolve project_info.json
    source = args.source
    if source.is_dir():
        candidates = [
            source / "project_info.json",
            source / ".coverage-tiers" / "project_info.json",
        ]
        source = next((c for c in candidates if c.exists()), None)
        if source is None:
            print(
                "[ERROR] No project_info.json found. Run analyze_project_structure.py first.",
                file=sys.stderr,
            )
            return 1

    data = read_json(source)
    try:
        language = Language(data["language"])
    except (ValueError, KeyError):
        language = Language.UNKNOWN

    frameworks = data.get("frameworks", [])
    try:
        test_framework = TestFramework(data.get("test_framework", "unknown"))
    except ValueError:
        test_framework = TestFramework.UNKNOWN

    project_name = args.project_name or Path(data.get("root_path", "project")).name

    workflow_yaml = generate_workflow(language, frameworks, test_framework, project_name)
    makefile_target = generate_makefile_target(language)
    npm_scripts = generate_npm_scripts(language)

    if args.dry_run or not args.output:
        print("# === .github/workflows/coverage.yml ===")
        print(workflow_yaml)
        print()
        print("# === Makefile targets ===")
        print(makefile_target)
        if npm_scripts:
            print()
            print("# === package.json scripts ===")
            print(npm_scripts)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(workflow_yaml, encoding="utf-8")
        print(f"Workflow written to {args.output}", file=sys.stderr)

    if args.makefile and not args.dry_run:
        with args.makefile.open("a", encoding="utf-8") as f:
            f.write("\n")
            f.write(makefile_target)
        print(f"Makefile targets appended to {args.makefile}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
