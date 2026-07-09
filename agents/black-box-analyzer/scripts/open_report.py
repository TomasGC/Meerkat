#!/usr/bin/env python3
"""One-command pipeline: collect → merge → ReportGenerator → open browser.

Steps:
  1. collect_runtime_coverage.py  → .coverage-tiers/*.lcov
  2. lcov --add-tracefile          → .coverage-tiers/combined.lcov
  3. reportgenerator               → coverage-report/index.html
  4. Open browser (cross-platform)

Usage:
    python open_report.py /path/to/project
    python open_report.py /path/to/project --tiers unit int_mock
    python open_report.py /path/to/project --skip-collect          # reuse existing lcov files
    python open_report.py /path/to/project --skip-merge            # skip lcov merge
    python open_report.py /path/to/project --no-browser            # don't open browser
    python open_report.py /path/to/project --report-dir ./report
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

TIERS = ("unit", "int_mock", "int_real", "e2e")


def _run(cmd: list[str], cwd: Path, label: str) -> int:
    print(f"\n[{label}] $ {' '.join(str(x) for x in cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        print(f"[{label}] FAILED (rc={result.returncode})", file=sys.stderr)
    return result.returncode


def step_collect(project_path: Path, output_dir: Path, tiers: tuple[str, ...]) -> list[Path]:
    """Run collect_runtime_coverage.py and return paths of generated lcov files."""
    collector = Path(__file__).parent / "collect_runtime_coverage.py"
    cmd = [
        sys.executable, str(collector),
        str(project_path),
        "--tiers", *tiers,
        "--output-dir", str(output_dir),
    ]
    rc = _run(cmd, project_path, "collect")
    if rc != 0:
        print("[WARN] Coverage collection had errors — continuing with available files", file=sys.stderr)

    return [output_dir / f"coverage_{tier}.lcov" for tier in tiers if (output_dir / f"coverage_{tier}.lcov").exists()]


def step_merge(lcov_files: list[Path], output: Path) -> bool:
    """Merge lcov files using lcov tool or fallback concatenation."""
    if not lcov_files:
        print("[merge] No lcov files to merge", file=sys.stderr)
        return False

    if shutil.which("lcov"):
        cmd = ["lcov"]
        for f in lcov_files:
            cmd += ["--add-tracefile", str(f)]
        cmd += ["--output-file", str(output), "--ignore-errors", "empty"]
        rc = _run(cmd, output.parent, "merge")
        if rc == 0:
            return True
        print("[WARN] lcov merge failed — falling back to concatenation", file=sys.stderr)

    # Fallback: concatenate
    print(f"[merge] Concatenating {len(lcov_files)} lcov files → {output}", file=sys.stderr)
    with output.open("w", encoding="utf-8") as out:
        for f in lcov_files:
            if f.exists():
                out.write(f.read_text(encoding="utf-8"))
                out.write("\n")
    return output.exists()


def step_reportgenerator(
    lcov_glob: str,
    report_dir: Path,
    project_name: str,
) -> bool:
    """Run ReportGenerator to produce HTML report."""
    rg = shutil.which("reportgenerator")
    if not rg:
        # Try dotnet tool
        result = subprocess.run(
            ["dotnet", "tool", "list", "--global"],
            capture_output=True, text=True,
        )
        if "reportgenerator" in result.stdout.lower():
            rg = "reportgenerator"

    if not rg:
        print(
            "[WARN] ReportGenerator not found.\n"
            "Install: dotnet tool install --global dotnet-reportgenerator-globaltool\n"
            "Skipping HTML report generation.",
            file=sys.stderr,
        )
        return False

    report_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        rg,
        f"-reports:{lcov_glob}",
        f"-targetdir:{report_dir}",
        "-reporttypes:Html;HtmlSummary;Badges;JsonSummary",
        f"-title:{project_name} Coverage",
        "-verbosity:Warning",
    ]
    rc = _run(cmd, report_dir.parent, "reportgenerator")
    return rc == 0


def step_open_browser(index_html: Path) -> None:
    """Open HTML report in default browser (cross-platform)."""
    url = index_html.resolve().as_uri()
    print(f"\n[browser] Opening {url}", file=sys.stderr)
    system = platform.system()
    if system == "Windows":
        os.startfile(str(index_html.resolve()))
    elif system == "Darwin":
        subprocess.run(["open", url])
    else:
        subprocess.run(["xdg-open", url])


def print_summary(report_dir: Path, lcov_files: list[Path], combined: Path) -> None:
    """Print a quick text summary from ReportGenerator's JsonSummary if available."""
    summary_file = report_dir / "Summary.json"
    if not summary_file.exists():
        return

    import json
    try:
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        print("\n── Coverage Summary ──────────────────────────────────", file=sys.stderr)
        print(f"  Line coverage   : {summary.get('linecoverage', 'n/a')}%", file=sys.stderr)
        print(f"  Branch coverage : {summary.get('branchcoverage', 'n/a')}%", file=sys.stderr)
        print(f"  Coverable lines : {summary.get('coverablelines', 'n/a')}", file=sys.stderr)
        print(f"  Covered lines   : {summary.get('coveredlines', 'n/a')}", file=sys.stderr)
        assemblies = summary.get('assemblies', [])
        total_classes = sum(len(a.get('classes', [])) for a in assemblies)
        print(f"  Files (classes) : {total_classes}", file=sys.stderr)
        print("─────────────────────────────────────────────────────", file=sys.stderr)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="collect → merge → ReportGenerator → open browser (one command)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python open_report.py /path/to/project
  python open_report.py /path/to/project --tiers unit int_mock
  python open_report.py /path/to/project --skip-collect      # reuse .coverage-tiers/*.lcov
  python open_report.py /path/to/project --no-browser        # headless / CI mode
  python open_report.py /path/to/project --report-dir ./report
        """,
    )
    parser.add_argument("project_path", type=Path)
    parser.add_argument(
        "--tiers",
        nargs="+",
        choices=list(TIERS),
        default=list(TIERS),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for lcov files (default: <project>/.coverage-tiers)",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Directory for HTML report (default: <project>/coverage-report)",
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Skip test execution — use existing lcov files",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Skip lcov merge — pass individual files to ReportGenerator",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser (useful in headless / CI environments)",
    )
    parser.add_argument(
        "--project-name",
        default=None,
    )
    args = parser.parse_args()

    project_path = args.project_path.resolve()
    output_dir = args.output_dir or (project_path / ".coverage-tiers")
    report_dir = args.report_dir or (project_path / "coverage-report")
    project_name = args.project_name or project_path.name

    # ── Step 1: Collect ──────────────────────────────────────────────────────
    if args.skip_collect:
        print("[collect] Skipping — using existing lcov files", file=sys.stderr)
        lcov_files = [output_dir / f"coverage_{t}.lcov" for t in args.tiers if (output_dir / f"coverage_{t}.lcov").exists()]
        if not lcov_files:
            print(f"[ERROR] No lcov files found in {output_dir}", file=sys.stderr)
            return 1
        print(f"[collect] Found {len(lcov_files)} existing lcov files", file=sys.stderr)
    else:
        lcov_files = step_collect(project_path, output_dir, tuple(args.tiers))
        if not lcov_files:
            print("[ERROR] No lcov files generated — check test runner setup", file=sys.stderr)
            return 1

    # ── Step 2: Merge ────────────────────────────────────────────────────────
    combined = output_dir / "combined.lcov"
    if args.skip_merge:
        lcov_glob = str(output_dir / "*.lcov")
    else:
        ok = step_merge(lcov_files, combined)
        lcov_glob = str(combined) if ok else str(output_dir / "*.lcov")

    # ── Step 3: ReportGenerator ──────────────────────────────────────────────
    ok = step_reportgenerator(lcov_glob, report_dir, project_name)
    if not ok:
        print(f"\n[INFO] Raw lcov files available in: {output_dir}", file=sys.stderr)
        if combined.exists():
            print(f"[INFO] Combined lcov: {combined}", file=sys.stderr)
        return 1

    # ── Step 4: Summary + open browser ──────────────────────────────────────
    print_summary(report_dir, lcov_files, combined)

    index_html = report_dir / "index.html"
    if index_html.exists():
        print(f"\nReport: {index_html}", file=sys.stderr)
        if not args.no_browser:
            step_open_browser(index_html)
    else:
        print(f"[WARN] index.html not found in {report_dir}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
