#!/usr/bin/env python3
"""Shared orchestrator — registry dispatch, ThreadPool fan-out, progress, output shaping.

An agent's own orchestrate.py supplies the checker registry, thread count,
display label and app name, and cache directory; this module owns everything
else: CLI parsing, incremental file discovery, streaming progress, dedup,
severity filtering, and json/table output.
"""

import argparse
import importlib
import inspect
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.engine.cache import clear_cache
from lib.engine.discovery import detect_language, get_branch_files, get_changed_files, get_staged_files

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _progress_bar(completed: int, total: int, width: int = 28) -> str:
    filled = int(width * completed / total) if total else 0
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * completed / total) if total else 0
    return f"[{bar}] {completed}/{total} ({pct}%)"


def _mini_bar(count: int, max_count: int, width: int = 8) -> str:
    if max_count == 0:
        return "░" * width
    filled = min(width, int(width * count / max_count))
    return "█" * filled + "░" * (width - filled)


def _detect_base_branch(path: Path) -> str | None:
    for branch in ("main", "master"):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            capture_output=True, cwd=str(path), timeout=5,
        )
        if r.returncode == 0:
            return branch
    return None


def _run_checker(
    name: str,
    module_path: str,
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    cache_ttl_days: int = 7,
    role: str | None = None,
) -> dict:
    try:
        mod = importlib.import_module(module_path)
        params = inspect.signature(mod.run).parameters
        kwargs: dict = {}
        if "files" in params and files is not None:
            kwargs["files"] = files
        if "agents" in params:
            kwargs["agents"] = agents
        if "no_cache" in params:
            kwargs["no_cache"] = no_cache
        if "cache_ttl_days" in params:
            kwargs["cache_ttl_days"] = cache_ttl_days
        if "role" in params and role is not None:
            kwargs["role"] = role
        return mod.run(path, language, **kwargs)
    except Exception as exc:
        return {
            "principle": name,
            "success": False,
            "error": str(exc),
            "violations": [],
            "files_analyzed": 0,
            "duration_ms": 0,
        }


def _build_summary(results: list[dict]) -> dict:
    summary = {}
    for result in results:
        principle = result.get("principle", "unknown")
        violations = result.get("violations", [])
        counts = {"count": len(violations), "high": 0, "medium": 0, "low": 0}
        for v in violations:
            sev = v.get("severity", "low")
            if sev in counts:
                counts[sev] += 1
        summary[principle] = counts
    return summary


def _print_table(violations: list[dict], label_singular: str) -> None:
    if not violations:
        print("No violations found.")
        return

    col_w = [8, 22, 45, 55]
    header = (
        f"{'SEVERITY':<{col_w[0]}} | "
        f"{label_singular.upper():<{col_w[1]}} | "
        f"{'FILE:LINE':<{col_w[2]}} | "
        f"{'MESSAGE':<{col_w[3]}}"
    )
    sep = "-" * len(header)
    print(header)
    print(sep)
    for v in violations:
        file_line = f"{v.get('file', '?')}:{v.get('line', 0)}"
        print(
            f"{v.get('severity', '?').upper():<{col_w[0]}} | "
            f"{v.get('principle', '?'):<{col_w[1]}} | "
            f"{file_line[:col_w[2]]:<{col_w[2]}} | "
            f"{str(v.get('message', ''))[:col_w[3]]}"
        )


def _estimate_token_savings(total_violations: int, checkers_run: int) -> int:
    return checkers_run * 2000 + total_violations * 200


def main(
    *,
    registry: dict[str, str],
    app_name: str,
    label_singular: str,
    cache_dir: Path,
    max_workers: int = 5,
    argv: list[str] | None = None,
) -> None:
    """Run the CLI. `label_singular` is "checker" or "principle" — drives column
    headers and the "Summary by X" line. `app_name` drives the banner text.
    """
    parser = argparse.ArgumentParser(description=app_name)
    parser.add_argument("--path", "-p", type=Path, default=Path.cwd(),
                        help="Path to analyze (default: cwd)")
    parser.add_argument("--checks", "-c", default="all",
                        help="Comma-separated checkers or 'all' (default: all)")
    parser.add_argument("--format", "-f", choices=["json", "table"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output file path (default: stdout)")
    parser.add_argument("--top", "-n", type=int, default=None,
                        help="Limit output to top N violations by severity")
    parser.add_argument("--min-severity", choices=["high", "medium", "low"], default="low",
                        help="Minimum severity to include (default: low = all)")
    parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=True,
                        help="Stream checker progress to stderr as each finishes (default: on)")
    parser.add_argument("--since", default=None, metavar="REF",
                        help="Incremental: only analyze files changed since git ref (e.g. HEAD~1, main)")
    parser.add_argument("--staged", action="store_true",
                        help="Incremental: only analyze git staged files")
    parser.add_argument("--agents", type=int, default=1, metavar="N",
                        help="Run N independent local AI calls per file, dedup-merge (default: 1)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass per-file local AI result cache")
    parser.add_argument("--cache-ttl", type=int, default=7, metavar="DAYS",
                        help="Cache TTL in days; 0 = never expire (default: 7)")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Delete all cached results and exit")
    parser.add_argument("--full", action="store_true",
                        help="Full-repo analysis, bypass auto branch-vs-main detection")
    model_group = parser.add_mutually_exclusive_group()
    model_group.add_argument("--role", default=None, metavar="ROLE",
                             help="Override model role for all semantic checkers (analyzer, fast, deep, reasoning)")
    model_group.add_argument("--fast", action="store_true",
                             help="Use 'fast' role for all semantic checkers")
    args = parser.parse_args(argv)
    if args.fast:
        args.role = "fast"

    if args.clear_cache:
        n = clear_cache(cache_dir)
        print(f"[OK] Cleared {n} cache entries", file=sys.stderr)
        sys.exit(0)

    path = args.path.resolve()
    if not path.exists():
        print(f"[ERROR] Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if args.checks.strip().lower() == "all":
        selected = list(registry.items())
    else:
        keys = [k.strip() for k in args.checks.split(",")]
        selected = [(k, registry[k]) for k in keys if k in registry]
        unknown = [k for k in keys if k not in registry]
        if unknown:
            print(f"[WARN] Unknown checkers: {', '.join(unknown)}", file=sys.stderr)

    language = detect_language(path)

    incremental_files: list | None = None
    if args.staged:
        incremental_files = get_staged_files(path)
        if incremental_files is not None:
            print(f"[Incremental] staged: {len(incremental_files)} files", file=sys.stderr, flush=True)
        else:
            print("[Incremental] --staged: not a git repo; running full analysis", file=sys.stderr)
    elif args.since:
        incremental_files = get_changed_files(path, since=args.since)
        if incremental_files is not None:
            print(f"[Incremental] changed since {args.since}: {len(incremental_files)} files",
                  file=sys.stderr, flush=True)
        else:
            print(f"[Incremental] --since: not a git repo; running full analysis", file=sys.stderr)
    elif not args.full:
        base = _detect_base_branch(path)
        if base:
            incremental_files = get_branch_files(path, base)
            if incremental_files is not None:
                print(f"[Auto] branch vs {base}: {len(incremental_files)} changed files",
                      file=sys.stderr, flush=True)
            else:
                print(f"[Auto] not a git repo or no changes vs {base}; running full analysis",
                      file=sys.stderr, flush=True)
        else:
            print("[Auto] base branch not found; running full analysis", file=sys.stderr, flush=True)

    if args.stream:
        mode = f"incremental ({len(incremental_files)} files)" if incremental_files is not None else "full"
        print(f"\n{app_name} — {path} ({language}) [{mode}]", file=sys.stderr, flush=True)
        if args.agents > 1:
            print(f"Local AI agents: {args.agents}x per file (dedup-merged)", file=sys.stderr, flush=True)
        print(f"Running {len(selected)} checkers...\n", file=sys.stderr, flush=True)

    start_total = time.time()
    total_checkers = len(selected)

    _completed: list[dict] = []
    _results_lock = threading.Lock()
    _completed_count = [0]

    def on_checker_done(future, checker_name: str) -> None:
        try:
            result = future.result()
        except Exception as exc:
            result = {
                "principle": checker_name,
                "success": False,
                "violations": [],
                "error": str(exc),
                "files_analyzed": 0,
                "duration_ms": 0,
            }
        with _results_lock:
            _completed.append(result)
            _completed_count[0] += 1
            n_done = _completed_count[0]

        if args.stream:
            status = "✓" if result.get("success") else "✗"
            n = len(result.get("violations", []))
            ms = result.get("duration_ms", 0)
            hits = result.get("cache_hits", 0)
            cache_str = f" [cache:{hits}]" if hits else ""
            bar = _progress_bar(n_done, total_checkers)
            print(
                f"  {bar}  {status} {result.get('principle', checker_name):<22} "
                f"{n:>3} violations  ({ms}ms){cache_str}",
                file=sys.stderr, flush=True,
            )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for name, mod_path in selected:
            future = executor.submit(
                _run_checker, name, mod_path, path, language,
                incremental_files, args.agents, args.no_cache, args.cache_ttl, args.role,
            )
            future.add_done_callback(lambda f, n=name: on_checker_done(f, n))

    results = _completed

    all_violations: list[dict] = []
    _seen: set[tuple] = set()
    for result in results:
        for v in result.get("violations", []):
            key = (v.get("file"), v.get("line"), v.get("principle"))
            if key not in _seen:
                _seen.add(key)
                all_violations.append(v)

    _min_sev = _SEVERITY_ORDER.get(args.min_severity, 2)
    all_violations = [v for v in all_violations
                      if _SEVERITY_ORDER.get(v.get("severity", "low"), 2) <= _min_sev]
    all_violations.sort(key=lambda v: _SEVERITY_ORDER.get(v.get("severity", "low"), 2))

    if args.top:
        all_violations = all_violations[: args.top]

    total_time = int((time.time() - start_total) * 1000)
    total_files = max((r.get("files_analyzed", 0) for r in results), default=0)
    summary = _build_summary(results)

    cache_hits = sum(r.get("cache_hits", 0) for r in results)
    cache_total = sum(r.get("cache_total", 0) for r in results)

    if args.stream:
        max_count = max((summary[p]["count"] for p in summary), default=1) or 1
        print(f"\n{'─' * 60}", file=sys.stderr, flush=True)
        for principle, counts in sorted(summary.items(), key=lambda x: -x[1]["count"]):
            bar = _mini_bar(counts["count"], max_count)
            print(
                f"  {principle:<28} {bar}  {counts['count']:>3}  "
                f"({counts['high']}H {counts['medium']}M {counts['low']}L)",
                file=sys.stderr, flush=True,
            )
        print(f"{'─' * 60}", file=sys.stderr, flush=True)
        print(
            f"  Total: {len(all_violations)} violations  |  {total_time}ms",
            file=sys.stderr, flush=True,
        )
        if cache_hits:
            saved_s = round(cache_hits * 1.5)
            print(
                f"  Cache: {cache_hits} hits / {cache_total} files  (~{saved_s}s saved)",
                file=sys.stderr, flush=True,
            )

    output_data: dict = {
        "success": True,
        "path": str(path),
        "language": language,
        "analysis_time_ms": total_time,
        "files_analyzed": total_files,
        "total_violations": len(all_violations),
        "checkers_run": len(selected),
        "summary": summary,
        "violations": all_violations,
        "estimated_token_savings": _estimate_token_savings(len(all_violations), len(selected)),
    }
    if cache_hits or cache_total:
        output_data["cache"] = {"hits": cache_hits, "total": cache_total}
    if incremental_files is not None:
        output_data["incremental_files"] = len(incremental_files)

    if args.format == "table":
        print(f"\n{app_name} — {path} ({language})")
        print(f"Files: {total_files} | Violations: {len(all_violations)} | Time: {total_time}ms\n")
        _print_table(all_violations, label_singular)
        print(f"\nSummary by {label_singular}:")
        for principle, counts in sorted(summary.items()):
            print(f"  {principle:<28} {counts['count']:>3} total  "
                  f"({counts['high']} high, {counts['medium']} medium, {counts['low']} low)")
    else:
        json_str = json.dumps(output_data, indent=2)
        if args.output:
            args.output.write_text(json_str, encoding="utf-8")
            print(f"[OK] Results written to {args.output}", file=sys.stderr)
        else:
            print(json_str)
