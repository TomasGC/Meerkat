#!/usr/bin/env python3
"""Clean Code Analyzer orchestrator.

Runs all 11 principle checkers in parallel via ThreadPoolExecutor with callback streaming.
Usage:
  python orchestrate.py --path /project --checks all --format json
  python orchestrate.py --path /project --checks solid,dry --format table
  python orchestrate.py --path /project --format json --output results.json
  python orchestrate.py --path /project --since HEAD~1           # incremental: changed files only
  python orchestrate.py --path /project --staged                 # incremental: staged files only
  python orchestrate.py --path /project --agents 2               # 2x local AI calls per file, dedup-merged
  python orchestrate.py --path /project --no-cache               # bypass per-file local AI cache
  python orchestrate.py --path /project --clear-cache            # delete all cached results
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
_GLOBAL_SCRIPTS = Path.home() / ".claude" / "scripts"
if str(_GLOBAL_SCRIPTS) not in sys.path:
    sys.path.append(str(_GLOBAL_SCRIPTS))

from lib.engine.orchestrator import (  # noqa: F401 — re-exported for tests/unit/test_orchestrate_unit.py
    _build_summary,
    _detect_base_branch,
    _estimate_token_savings,
    _mini_bar,
    _progress_bar,
    _run_checker,
)
from lib.engine.orchestrator import main as _engine_main

CHECKERS: dict[str, str] = {
    "dry": "checkers.check_dry",
    "solid": "checkers.check_solid",
    "kiss": "checkers.check_kiss",
    "yagni": "checkers.check_yagni",
    "naming": "checkers.check_naming",
    "comments": "checkers.check_comments",
    "cqrs": "checkers.check_cqrs",
    "ddd": "checkers.check_ddd",
    "lod": "checkers.check_lod",
    "slap": "checkers.check_slap",
    "inheritance": "checkers.check_inheritance",
}

_CACHE_DIR = Path.home() / ".claude" / "agents" / "clean-code-analyzer" / ".cache"
_CACHE_ENV_VAR = "CCA_CACHE_DIR"


def _cache_dir() -> Path:
    """Cache root, overridable via CCA_CACHE_DIR.

    Read on every call rather than captured at import time so tests (including
    subprocess-based ones) can redirect it away from the real user cache.
    """
    override = os.environ.get(_CACHE_ENV_VAR)
    return Path(override) if override else _CACHE_DIR


def main() -> None:
    _engine_main(
        registry=CHECKERS,
        app_name="Clean Code Analysis",
        label_singular="principle",
        cache_dir=_cache_dir(),
        max_workers=6,
    )


if __name__ == "__main__":
    main()
