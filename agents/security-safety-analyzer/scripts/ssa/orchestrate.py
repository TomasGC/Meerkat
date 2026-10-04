#!/usr/bin/env python3
"""
Security Safety Analyzer orchestrator.

Runs all 5 safety/security checkers in parallel via ThreadPoolExecutor with callback streaming.
Usage:
  python orchestrate.py --path /project --checks all --format json
  python orchestrate.py --path /project --checks security,crash_bugs --format table
  python orchestrate.py --path /project --format json --output results.json
  python orchestrate.py --path /project --since HEAD~1           # incremental: changed files only
  python orchestrate.py --path /project --staged                 # incremental: staged files only
  python orchestrate.py --path /project --agents 2               # 2x local AI calls per file, dedup-merged
  python orchestrate.py --path /project --no-cache               # bypass per-file local AI cache
  python orchestrate.py --path /project --clear-cache            # delete all cached results
"""



from lib.engine.orchestrator import (  # noqa: F401 — re-exported for tests/unit/test_orchestrate.py
    _build_summary,
    _detect_base_branch,
    _estimate_token_savings,
    _mini_bar,
    _progress_bar,
    _run_checker,
)
from lib import paths
from lib.engine.orchestrator import main as _engine_main

CHECKERS: dict[str, str] = {
    "security": "ssa.checkers.check_security",
    "crypto": "ssa.checkers.check_crypto",
    "deserialization": "ssa.checkers.check_deserialization",
    "misconfiguration": "ssa.checkers.check_misconfiguration",
    "sensitive_data": "ssa.checkers.check_sensitive_data",
    "crash_bugs": "ssa.checkers.check_crash_bugs",
    "concurrency": "ssa.checkers.check_concurrency",
    "resource_leaks": "ssa.checkers.check_resource_leaks",
    "error_handling": "ssa.checkers.check_error_handling",
    "prompt_injection": "ssa.checkers.check_prompt_injection",
}

_CACHE_DIR = paths.user_root() / "agents" / "security-safety-analyzer" / ".cache"


def main() -> None:
    _engine_main(
        registry=CHECKERS,
        app_name="Security Safety Analysis",
        label_singular="checker",
        cache_dir=_CACHE_DIR,
        max_workers=5,
    )


if __name__ == "__main__":
    main()
