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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
_GLOBAL_SCRIPTS = Path.home() / ".claude" / "scripts"
if str(_GLOBAL_SCRIPTS) not in sys.path:
    sys.path.append(str(_GLOBAL_SCRIPTS))

from lib.engine.orchestrator import (  # noqa: F401 — re-exported for tests/unit/test_orchestrate.py
    _build_summary,
    _detect_base_branch,
    _estimate_token_savings,
    _mini_bar,
    _progress_bar,
    _run_checker,
)
from lib.engine.orchestrator import main as _engine_main

CHECKERS: dict[str, str] = {
    "security": "checkers.check_security",
    "crypto": "checkers.check_crypto",
    "deserialization": "checkers.check_deserialization",
    "misconfiguration": "checkers.check_misconfiguration",
    "sensitive_data": "checkers.check_sensitive_data",
    "crash_bugs": "checkers.check_crash_bugs",
    "concurrency": "checkers.check_concurrency",
    "resource_leaks": "checkers.check_resource_leaks",
    "error_handling": "checkers.check_error_handling",
    "prompt_injection": "checkers.check_prompt_injection",
}

_CACHE_DIR = Path.home() / ".claude" / "agents" / "security-safety-analyzer" / ".cache"


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
