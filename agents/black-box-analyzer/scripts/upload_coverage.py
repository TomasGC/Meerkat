#!/usr/bin/env python3
"""Upload per-tier lcov files to Codecov with flags.

Reads a manifest JSON produced by collect_runtime_coverage.py,
then uploads each tier's lcov file to Codecov with the matching
flag (--flag unit, --flag int_mock, --flag int_real, --flag e2e).

Requires:
    codecov CLI: pip install codecov  OR  curl -Os https://uploader.codecov.io/latest/linux/codecov
    CODECOV_TOKEN env var (required for private repos, optional for public)

Usage:
    python upload_coverage.py manifest.json
    python upload_coverage.py manifest.json --repo owner/repo --commit abc123
    python upload_coverage.py --lcov-dir .coverage-tiers  # auto-discover lcov files
    python upload_coverage.py manifest.json --dry-run
    python upload_coverage.py manifest.json --merge  # also merge all tiers into combined.lcov

The Codecov dashboard will then show per-flag coverage and delta:
    https://app.codecov.io/<owner>/<repo>/flags
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TIER_FLAGS = ("unit", "int_mock", "int_real", "e2e")


def _find_codecov() -> str | None:
    """Locate codecov uploader binary."""
    for name in ("codecov", "codecov.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _merge_lcov(lcov_files: list[Path], output: Path) -> bool:
    """Merge multiple lcov files using lcov --add-tracefile (requires lcov package)."""
    if not shutil.which("lcov"):
        # Fallback: naive concatenation (not accurate but better than nothing)
        with output.open("w", encoding="utf-8") as out:
            for f in lcov_files:
                if f.exists():
                    out.write(f.read_text(encoding="utf-8"))
                    out.write("\n")
        print(f"[WARN] lcov tool not found — files concatenated (not merged) → {output}", file=sys.stderr)
        return True

    cmd = ["lcov"]
    for f in lcov_files:
        if f.exists():
            cmd += ["--add-tracefile", str(f)]
    cmd += ["--output-file", str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] lcov merge failed: {result.stderr[:300]}", file=sys.stderr)
        return False
    return True


def upload_with_codecov(
    lcov_file: Path,
    flag: str,
    repo: str | None,
    commit: str | None,
    branch: str | None,
    pr: str | None,
    token: str | None,
    dry_run: bool,
    codecov_bin: str,
) -> int:
    cmd = [
        codecov_bin,
        "--file", str(lcov_file),
        "--flag", flag,
        "--name", f"coverage-{flag}",
        "--nonZero",
    ]
    if token:
        cmd += ["--token", token]
    if repo:
        cmd += ["--slug", repo]
    if commit:
        cmd += ["--sha", commit]
    if branch:
        cmd += ["--branch", branch]
    if pr:
        cmd += ["--pr", pr]

    log_cmd = [c if token is None or c != token else "***" for c in cmd]
    print(f"  $ {' '.join(log_cmd)}", file=sys.stderr)
    if dry_run:
        return 0

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Codecov upload flag={flag} failed:\n{result.stderr[:500]}", file=sys.stderr)
    else:
        # Extract URL from output
        for line in result.stdout.splitlines():
            if "codecov.io" in line:
                print(f"  {line.strip()}", file=sys.stderr)
    return result.returncode


def load_manifest(manifest_path: Path) -> dict[str, Path]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {tier: Path(path) for tier, path in data.items()}


def discover_lcov_dir(lcov_dir: Path) -> dict[str, Path]:
    """Auto-discover coverage_{tier}.lcov files in a directory."""
    result = {}
    for tier in TIER_FLAGS:
        candidate = lcov_dir / f"coverage_{tier}.lcov"
        if candidate.exists():
            result[tier] = candidate
        else:
            # Also check lcov.info inside a tier subdirectory
            candidate2 = lcov_dir / tier / "lcov.info"
            if candidate2.exists():
                result[tier] = candidate2
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Upload per-tier lcov files to Codecov with flags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_coverage.py manifest.json
  python upload_coverage.py manifest.json --dry-run
  python upload_coverage.py manifest.json --repo octocat/hello-world --commit abc123
  python upload_coverage.py --lcov-dir .coverage-tiers --repo owner/repo
  python upload_coverage.py manifest.json --merge --merged-output combined.lcov

Environment variables:
  CODECOV_TOKEN   Codecov upload token (required for private repos)
  CODECOV_SLUG    Repository slug (owner/repo) — overridden by --repo
        """,
    )
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        help="JSON manifest from collect_runtime_coverage.py",
    )
    parser.add_argument(
        "--lcov-dir",
        type=Path,
        help="Auto-discover lcov files in this directory (alternative to manifest)",
    )
    parser.add_argument("--repo", help="Repository slug (owner/repo)")
    parser.add_argument("--commit", help="Commit SHA")
    parser.add_argument("--branch", help="Branch name")
    parser.add_argument("--pr", help="Pull request number")
    parser.add_argument(
        "--tiers",
        nargs="+",
        choices=list(TIER_FLAGS),
        default=list(TIER_FLAGS),
        help="Tiers to upload (default: all found)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands, don't upload")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Also merge all tier files and upload as combined (no flag)",
    )
    parser.add_argument(
        "--merged-output",
        type=Path,
        default=None,
        help="Output path for merged lcov (default: <lcov-dir>/combined.lcov)",
    )
    parser.add_argument(
        "--codecov-bin",
        default=None,
        help="Path to codecov binary (auto-detected if not set)",
    )
    args = parser.parse_args()

    # Resolve lcov files
    if args.manifest:
        lcov_files = load_manifest(args.manifest)
    elif args.lcov_dir:
        lcov_files = discover_lcov_dir(args.lcov_dir)
    else:
        parser.error("Provide either a manifest file or --lcov-dir")

    if not lcov_files:
        print("[ERROR] No lcov files found", file=sys.stderr)
        return 1

    # Resolve codecov binary
    codecov_bin = args.codecov_bin or _find_codecov()
    if not codecov_bin and not args.dry_run:
        print(
            "[ERROR] codecov binary not found.\n"
            "Install: pip install codecov\n"
            "     or: curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov",
            file=sys.stderr,
        )
        return 1
    if args.dry_run and not codecov_bin:
        codecov_bin = "codecov"  # placeholder for dry-run output

    token = os.environ.get("CODECOV_TOKEN")
    repo = args.repo or os.environ.get("CODECOV_SLUG")

    errors = 0
    uploaded = []

    for tier in args.tiers:
        lcov_path = lcov_files.get(tier)
        if not lcov_path:
            print(f"[SKIP] No lcov file for tier={tier}", file=sys.stderr)
            continue
        if not args.dry_run and not lcov_path.exists():
            print(f"[SKIP] File not found: {lcov_path}", file=sys.stderr)
            continue

        print(f"Uploading tier={tier} flag={tier} file={lcov_path}", file=sys.stderr)
        rc = upload_with_codecov(
            lcov_path,
            flag=tier,
            repo=repo,
            commit=args.commit,
            branch=args.branch,
            pr=args.pr,
            token=token,
            dry_run=args.dry_run,
            codecov_bin=codecov_bin,
        )
        if rc == 0:
            uploaded.append(tier)
        else:
            errors += 1

    # Merge and upload combined
    if args.merge and lcov_files:
        existing = [p for p in lcov_files.values() if args.dry_run or p.exists()]
        if existing:
            merged_output = args.merged_output
            if not merged_output:
                base = args.lcov_dir or existing[0].parent
                merged_output = base / "combined.lcov"

            ok = _merge_lcov(existing, merged_output) if not args.dry_run else True
            if ok:
                print(f"Uploading merged (all tiers) → {merged_output}", file=sys.stderr)
                rc = upload_with_codecov(
                    merged_output,
                    flag="combined",
                    repo=repo,
                    commit=args.commit,
                    branch=args.branch,
                    pr=args.pr,
                    token=token,
                    dry_run=args.dry_run,
                    codecov_bin=codecov_bin,
                )
                if rc == 0:
                    uploaded.append("combined")
                else:
                    errors += 1

    print(json.dumps({"uploaded": uploaded, "errors": errors}))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
