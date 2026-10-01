#!/usr/bin/env python3
"""YAGNI checker — dead code detection + local AI speculative feature scan."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.engine.hybrid import run_hybrid
from common.model_utils import PROMPTS_DIR

_PROMPT = "yagni_speculative"
_FIND_UNUSED = Path.home() / ".claude/scripts/cli/find_unused_code.py"


def _mechanical(path: Path, files: list | None) -> tuple[list[dict], int]:
    violations = []
    files_analyzed = 0
    if _FIND_UNUSED.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(_FIND_UNUSED), "--path", str(path), "--format", "json"],
                capture_output=True, text=True, timeout=60,
            )
            raw = json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None
            if raw is None or raw.get("success") is False:
                reason = (raw or {}).get("error") or result.stderr.strip()[:200] or f"exit code {result.returncode}"
                print(f"[WARN] YAGNI: {_FIND_UNUSED.name} failed: {reason}", file=sys.stderr)
            else:
                files_analyzed = raw.get("files_analyzed", 0)
                for sym in raw.get("unused_symbols", []):
                    sym_file = sym.get("file", "")
                    if files is not None:
                        changed_names = {f.name for f in files}
                        if Path(sym_file).name not in changed_names:
                            continue
                    violations.append({
                        "principle": "YAGNI",
                        "file": sym_file,
                        "line": sym.get("line_start", 0),
                        "severity": "high" if sym.get("confidence") == "high" else "medium",
                        "message": f"Unused {sym.get('type', 'symbol')}: {sym.get('name', '?')}",
                        "suggestion": "Remove dead code to reduce maintenance burden",
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] YAGNI: {_FIND_UNUSED.name} failed: {type(exc).__name__}",
                  file=sys.stderr)
    return violations, files_analyzed


def _format(item: dict, rel: str) -> dict:
    return {
        "principle": "YAGNI", "file": rel, "line": item.get("line", 0),
        "severity": item.get("severity", "medium"),
        "message": f"Speculative [{item.get('pattern', '?')}]: {item.get('violation', '')}",
        "suggestion": item.get("suggestion", ""),
    }


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False, role: str = "analyzer",
        cache_dir: Path | None = None, cache_ttl_days: int = 7) -> dict:
    return run_hybrid(path, language, "YAGNI", _PROMPT, {}, PROMPTS_DIR,
                       files=files, agents=agents, no_cache=no_cache, role=role,
                       cache_dir=cache_dir, cache_ttl_days=cache_ttl_days,
                       mechanical_fn=_mechanical, format_ai_violation=_format)
