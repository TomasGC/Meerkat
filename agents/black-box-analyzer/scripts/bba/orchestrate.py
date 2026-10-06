#!/usr/bin/env python3
"""
Black-Box Analyzer orchestrator.

Primary entry point wrapping parallel_analyzer with aligned CLI surface.
Usage:
  python orchestrate.py --path /project
  python orchestrate.py --path /project --full
  python orchestrate.py --path /project --fast
  python orchestrate.py --path /project --role deep
  python orchestrate.py --path /project --agents 2
  python orchestrate.py --path /project --no-cache
  python orchestrate.py --path /project --clear-cache
  python orchestrate.py --path /project --format json
  python orchestrate.py --path /project --output results.json

Test-gap checkers (shared engine CLI — same flags as CCA and SSA):
  python orchestrate.py --gaps --path /project
  python orchestrate.py --gaps --path /project --full --checks unit,e2e --format table
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bba.cache import AnalysisCache, _cache_home, clear_model_cache
from lib.engine.cache import clear_cache

# One checker per test tier, run by lib.engine.orchestrator under --gaps
CHECKERS: dict[str, str] = {
    "unit": "bba.checkers.check_unit_gaps",
    "integ_mock": "bba.checkers.check_integ_mock_gaps",
    "integ_real": "bba.checkers.check_integ_real_gaps",
    "e2e": "bba.checkers.check_e2e_gaps",
}

_GAPS_SUBDIR = "gaps"


def _gaps_cache_dir() -> Path:
    """Per-file AI cache of the gap checkers, under the BBA cache root (honours BBA_CACHE_DIR)."""
    return _cache_home() / _GAPS_SUBDIR


def _run_gaps(argv: list[str]) -> None:
    from lib.engine.orchestrator import main as engine_main

    engine_main(
        registry=CHECKERS,
        app_name="Black-Box Analyzer — test gaps",
        label_singular="checker",
        cache_dir=_gaps_cache_dir(),
        max_workers=len(CHECKERS),
        argv=argv,
    )


def _detect_base_branch(path: Path) -> str | None:
    for branch in ("main", "master"):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            capture_output=True,
            cwd=str(path),
            timeout=5,
        )
        if r.returncode == 0:
            return branch
    return None


def _get_branch_files(path: Path, base: str) -> list[Path] | None:
    r = subprocess.run(
        ["git", "diff", f"{base}...HEAD", "--name-only"],
        capture_output=True,
        text=True,
        cwd=str(path),
        timeout=10,
    )
    if r.returncode != 0:
        return None
    files = [path / f.strip() for f in r.stdout.splitlines() if f.strip()]
    return [f for f in files if f.exists()] or None


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if "--gaps" in argv:
        _run_gaps([a for a in argv if a != "--gaps"])
        return

    parser = argparse.ArgumentParser(description="Black-Box Analyzer")
    parser.add_argument(
        "--gaps", action="store_true", help="Run the four test-gap checkers instead (engine CLI: see --gaps --help)"
    )
    parser.add_argument("--path", type=Path, default=Path("."), help="Project path to analyze")
    parser.add_argument("--full", action="store_true", help="Analyze entire repo (default: branch-vs-main incremental)")
    parser.add_argument("--fast", action="store_true", help="Use 'fast' model role (lighter, quicker)")
    parser.add_argument("--role", default=None, help="Override model role: analyzer, fast, deep, reasoning")
    parser.add_argument("--agents", type=int, default=1, help="N independent local AI calls per file, dedup-merged")
    parser.add_argument("--no-cache", action="store_true", dest="no_cache", help="Bypass per-file local AI cache")
    parser.add_argument(
        "--clear-cache", action="store_true", dest="clear_cache", help="Delete all cached local AI results and exit"
    )
    parser.add_argument("--format", choices=["json", "table", "summary"], default="table")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON output to file")
    args = parser.parse_args(argv)

    if args.clear_cache:
        cleared = clear_model_cache() + clear_cache(_gaps_cache_dir())
        # The analysis cache is separate from the model cache and must go too,
        # otherwise a "cleared" cache still serves stale AnalysisResults
        AnalysisCache().invalidate_all(include_projects=True)
        print(f"Cleared {cleared} cached result(s).")
        return

    role = args.role or ("fast" if args.fast else "analyzer")
    path = args.path.resolve()

    # Determine files: incremental by default, full if --full or no base branch found
    changed_files: list[Path] | None = None
    if not args.full:
        base = _detect_base_branch(path)
        if base:
            changed_files = _get_branch_files(path, base)
            if changed_files is not None:
                print(f"Incremental mode: {len(changed_files)} changed file(s) vs {base}", file=sys.stderr)
            else:
                print("No changed files detected vs base branch — nothing to analyze.", file=sys.stderr)
                return
        else:
            print("No main/master branch found — falling back to full analysis", file=sys.stderr)

    # parallel_analyzer.py takes project_path as a positional argument
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "parallel_analyzer.py"),
        str(path),
    ]
    if args.no_cache:
        cmd.append("--no-cache")
    if args.output:
        cmd.extend(["--output", str(args.output)])

    env = os.environ.copy()
    env["BBA_ROLE"] = role
    env["BBA_AGENTS"] = str(args.agents)
    if changed_files is not None:
        env["BBA_FILES"] = json.dumps([str(f) for f in changed_files])

    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
