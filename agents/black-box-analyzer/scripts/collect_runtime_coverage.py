#!/usr/bin/env python3
"""Instrument and run test suites to collect per-tier lcov coverage files.

Detects language/framework, runs each test tier (unit/integration/e2e)
with coverage enabled, emits separate lcov files ready for Codecov upload.

Supported stacks:
  Python  : pytest + pytest-cov  → lcov
  JS/TS   : jest (c8/nyc)        → lcov
  Go      : go test -coverprofile → converted to lcov via gcov2lcov
  Java    : gradle test + JaCoCo → lcov
  C#      : dotnet test + coverlet → lcov
  Rust    : cargo tarpaulin       → lcov

Usage:
    python collect_runtime_coverage.py /path/to/project
    python collect_runtime_coverage.py /path/to/project --tiers unit int_mock
    python collect_runtime_coverage.py /path/to/project --output-dir ./coverage
    python collect_runtime_coverage.py /path/to/project --dry-run
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyze_project_structure import detect_language
from common.models import Language

TIER_MARKERS = {
    "unit":     {"pytest": ["-m", "unit"],       "jest": "--testPathPattern=unit"},
    "int_mock": {"pytest": ["-m", "int_mock"],   "jest": "--testPathPattern=integration"},
    "int_real": {"pytest": ["-m", "int_real"],   "jest": "--testPathPattern=int_real"},
    "e2e":      {"pytest": ["-m", "e2e"],        "jest": "--testPathPattern=e2e"},
}

ALL_TIERS = ("unit", "int_mock", "int_real", "e2e")


def _run(cmd: list[str], cwd: Path, dry_run: bool) -> int:
    print(f"  $ {' '.join(cmd)}", file=sys.stderr)
    if dry_run:
        return 0
    result = subprocess.run(cmd, cwd=str(cwd))
    return result.returncode


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def collect_python(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run pytest with coverage per tier using markers."""
    if not _which("pytest"):
        print("[WARN] pytest not found — skipping Python coverage", file=sys.stderr)
        return {}

    outputs = {}
    for tier in tiers:
        lcov_file = output_dir / f"coverage_{tier}.lcov"
        marker = TIER_MARKERS[tier]["pytest"]
        cmd = [
            sys.executable, "-m", "pytest",
            *marker,
            f"--cov={project_path}",
            "--cov-report", f"lcov:{lcov_file}",
            "--cov-report", "term-missing:skip-covered",
            "-q",
        ]
        rc = _run(cmd, project_path, dry_run)
        if rc == 0 or (not dry_run and lcov_file.exists()):
            outputs[tier] = lcov_file
        else:
            print(f"[WARN] pytest tier={tier} failed (rc={rc})", file=sys.stderr)
    return outputs


def collect_js(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run jest with coverage per tier."""
    jest_bin = project_path / "node_modules" / ".bin" / "jest"
    jest_bin_win = jest_bin.parent / "jest.cmd"
    if not jest_bin.exists() and not jest_bin_win.exists() and not _which("jest"):
        print("[WARN] jest not found — skipping JS/TS coverage", file=sys.stderr)
        return {}

    jest_cmd = str(jest_bin_win) if jest_bin_win.exists() and not jest_bin.exists() else (str(jest_bin) if jest_bin.exists() else "jest")
    outputs = {}

    for tier in tiers:
        lcov_file = output_dir / f"coverage_{tier}.lcov"
        pattern = TIER_MARKERS[tier]["jest"]
        cmd = [
            jest_cmd,
            pattern,
            "--coverage",
            "--coverageReporters", "lcov",
            f"--coverageDirectory={output_dir / tier}",
            "--passWithNoTests",
        ]
        rc = _run(cmd, project_path, dry_run)
        generated = output_dir / tier / "lcov.info"
        if not dry_run and generated.exists():
            generated.replace(lcov_file)
            outputs[tier] = lcov_file
        elif dry_run:
            outputs[tier] = lcov_file
        else:
            print(f"[WARN] jest tier={tier} failed (rc={rc})", file=sys.stderr)
    return outputs


def collect_go(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run go test with coverprofile. Go doesn't support markers natively —
    uses build tags (//go:build unit) as convention."""
    if not _which("go"):
        print("[WARN] go not found — skipping Go coverage", file=sys.stderr)
        return {}

    outputs = {}
    for tier in tiers:
        cov_file = output_dir / f"coverage_{tier}.out"
        lcov_file = output_dir / f"coverage_{tier}.lcov"

        # Build tags map tiers to Go tags (convention: //go:build unit)
        tag = tier.replace("_", "")  # int_mock → intmock
        cmd = [
            "go", "test",
            f"-tags={tag}",
            f"-coverprofile={cov_file}",
            "-covermode=atomic",
            "./...",
        ]
        rc = _run(cmd, project_path, dry_run)

        # Convert .out → lcov using gcov2lcov (if available) or go tool cover -html
        if not dry_run and cov_file.exists():
            if _which("gcov2lcov"):
                rc2 = subprocess.run(
                    ["gcov2lcov", "-infile", str(cov_file), "-outfile", str(lcov_file)],
                    cwd=str(project_path),
                ).returncode
                if rc2 != 0:
                    print(f"[WARN] gcov2lcov failed (rc={rc2}) for tier={tier}", file=sys.stderr)
                    continue
            else:
                # Fallback: emit a minimal lcov from go coverage output
                _convert_go_cover_to_lcov(cov_file, lcov_file)
            outputs[tier] = lcov_file
        elif dry_run:
            outputs[tier] = lcov_file
        elif rc != 0:
            print(f"[WARN] go test tier={tier} failed (rc={rc})", file=sys.stderr)
        elif rc == 0:
            print(f"[WARN] go test tier={tier}: rc=0 but no coverage file at {cov_file}", file=sys.stderr)
    return outputs


def _convert_go_cover_to_lcov(cov_file: Path, lcov_file: Path) -> None:
    """Minimal .out → lcov conversion (line-level only, no branch data)."""
    lines = cov_file.read_text(encoding="utf-8").splitlines()
    lcov_lines = []
    current_file = None

    for line in lines[1:]:  # skip "mode: atomic"
        # format: path/to/file.go:startline.col,endline.col numstmt count
        parts = line.split(":")
        if len(parts) < 2:
            continue
        filepath = parts[0]
        rest = parts[1]
        try:
            startline = int(rest.split(",")[0].split(".")[0])
            count = int(rest.split(" ")[-1])
        except (ValueError, IndexError):
            continue

        if filepath != current_file:
            if current_file:
                lcov_lines.append("end_of_record")
            current_file = filepath
            lcov_lines.append(f"SF:{filepath}")

        lcov_lines.append(f"DA:{startline},{count}")

    if current_file:
        lcov_lines.append("end_of_record")

    lcov_file.write_text("\n".join(lcov_lines), encoding="utf-8")


def collect_dotnet(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run dotnet test with coverlet per tier using filter expressions."""
    if not _which("dotnet"):
        print("[WARN] dotnet not found — skipping C# coverage", file=sys.stderr)
        return {}

    outputs = {}
    # Tier → test filter category (MSTest/xUnit [Trait("Category", "...")])
    tier_filter = {
        "unit":     "Category=Unit",
        "int_mock": "Category=Integration",
        "int_real": "Category=IntegrationReal",
        "e2e":      "Category=E2E",
    }
    for tier in tiers:
        lcov_file = output_dir / f"coverage_{tier}.lcov"
        filt = tier_filter.get(tier, f"Category={tier}")
        cmd = [
            "dotnet", "test",
            f"--filter={filt}",
            f"--collect:XPlat Code Coverage",
            f"--results-directory={output_dir / tier}",
            "--",
            "DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=lcov",
        ]
        rc = _run(cmd, project_path, dry_run)

        # Find generated lcov file in results dir
        if not dry_run:
            generated_files = list((output_dir / tier).rglob("*.lcov"))
            if generated_files:
                generated_files[0].replace(lcov_file)
                outputs[tier] = lcov_file
            elif rc == 0:
                print(f"[WARN] dotnet tier={tier}: no lcov file generated", file=sys.stderr)
            else:
                print(f"[WARN] dotnet tier={tier} failed (rc={rc})", file=sys.stderr)
        elif dry_run:
            outputs[tier] = lcov_file
    return outputs


def collect_java(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run gradle test with JaCoCo per tier using test groups/tags."""
    gradle = project_path / "gradlew"
    gradle_cmd = str(gradle) if gradle.exists() else ("gradlew" if _which("gradlew") else "gradle")
    if not _which("gradle") and not gradle.exists() and not _which("gradlew"):
        print("[WARN] gradle not found — skipping Java coverage", file=sys.stderr)
        return {}

    outputs = {}
    tier_tags = {
        "unit": "unit",
        "int_mock": "integration",
        "int_real": "integrationReal",
        "e2e": "e2e",
    }
    for tier in tiers:
        lcov_file = output_dir / f"coverage_{tier}.lcov"
        tag = tier_tags.get(tier, tier)
        cmd = [
            gradle_cmd,
            "test",
            f"-Ptest.groups={tag}",
            "jacocoTestReport",
            f"-PjacocoReportDir={output_dir / tier}",
        ]
        rc = _run(cmd, project_path, dry_run)

        if not dry_run:
            # JaCoCo typically outputs xml/html; look for lcov if jacoco-to-lcov plugin used
            generated = list((output_dir / tier).rglob("lcov.info"))
            if generated:
                generated[0].rename(lcov_file)
                outputs[tier] = lcov_file
            else:
                print(
                    f"[WARN] Java tier={tier}: no lcov.info found — "
                    "ensure jacoco-to-cobertura or lcov plugin is configured",
                    file=sys.stderr,
                )
        elif dry_run:
            outputs[tier] = lcov_file
    return outputs


def collect_rust(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    """Run cargo tarpaulin per tier (Rust convention: #[cfg(test)] modules)."""
    if not _which("cargo"):
        print("[WARN] cargo not found — skipping Rust coverage", file=sys.stderr)
        return {}
    if not dry_run and not _which("cargo-tarpaulin"):
        print("[WARN] cargo-tarpaulin not installed — run: cargo install cargo-tarpaulin", file=sys.stderr)
        return {}

    outputs = {}
    # Rust has no built-in tier markers — use feature flags as convention:
    # [features]
    # test_unit = []
    # test_int_mock = []
    tier_features = {
        "unit":     "test_unit",
        "int_mock": "test_int_mock",
        "int_real": "test_int_real",
        "e2e":      "test_e2e",
    }
    for tier in tiers:
        lcov_file = output_dir / f"coverage_{tier}.lcov"
        feature = tier_features.get(tier, f"test_{tier}")
        cmd = [
            "cargo", "tarpaulin",
            f"--features={feature}",
            "--out", "Lcov",
            f"--output-dir={output_dir}",
        ]
        rc = _run(cmd, project_path, dry_run)
        generated = output_dir / "lcov.info"
        if not dry_run and generated.exists():
            generated.replace(lcov_file)
            outputs[tier] = lcov_file
        elif dry_run:
            outputs[tier] = lcov_file
        elif rc != 0:
            print(f"[WARN] cargo tarpaulin tier={tier} failed (rc={rc})", file=sys.stderr)
        else:
            print(f"[WARN] cargo tarpaulin tier={tier}: rc=0 but lcov.info not found in {output_dir}", file=sys.stderr)
    return outputs


_COLLECTORS = {
    Language.PYTHON:     collect_python,
    Language.TYPESCRIPT: collect_js,
    Language.JAVASCRIPT: collect_js,
    Language.GO:         collect_go,
    Language.CSHARP:     collect_dotnet,
    Language.JAVA:       collect_java,
    Language.KOTLIN:     collect_java,
    Language.RUST:       collect_rust,
}


def collect_coverage(
    project_path: Path,
    output_dir: Path,
    tiers: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Path]:
    language = detect_language(project_path)
    print(f"Detected language: {language.value}", file=sys.stderr)

    collector = _COLLECTORS.get(language)
    if collector is None:
        print(
            f"[WARN] No coverage collector for language={language.value}",
            file=sys.stderr,
        )
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    return collector(project_path, output_dir, tiers, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Collect per-tier (unit/int_mock/int_real/e2e) lcov coverage files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python collect_runtime_coverage.py /path/to/project
  python collect_runtime_coverage.py /path/to/project --tiers unit int_mock
  python collect_runtime_coverage.py /path/to/project --output-dir ./cov
  python collect_runtime_coverage.py /path/to/project --dry-run
        """,
    )
    parser.add_argument("project_path", type=Path)
    parser.add_argument(
        "--tiers",
        nargs="+",
        choices=list(ALL_TIERS),
        default=list(ALL_TIERS),
        help="Test tiers to collect (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Directory for lcov output files (default: <project>/.coverage-tiers)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON manifest of generated files to this path",
    )
    args = parser.parse_args()

    project_path = args.project_path.resolve()
    output_dir = args.output_dir or (project_path / ".coverage-tiers")

    outputs = collect_coverage(
        project_path,
        output_dir,
        tuple(args.tiers),
        args.dry_run,
    )

    manifest = {
        tier: str(path) for tier, path in outputs.items()
    }

    print(json.dumps(manifest, indent=2))

    if args.output:
        args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not outputs:
        print("[WARN] No coverage files generated", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
