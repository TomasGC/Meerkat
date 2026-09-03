#!/usr/bin/env python3
"""YAGNI checker — dead code detection + Ollama speculative feature scan."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.ollama_utils import analyze_files_parallel, check_ollama_available

_MODEL = "devstral"
_PROMPT = "yagni_speculative"
_FIND_UNUSED = Path.home() / ".claude/scripts/cli/agents/code_analyzer/find_unused_code.py"


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    model: str = _MODEL,
) -> dict:
    start = time.time()
    violations = []
    files_analyzed = 0

    # Part 1: dead code via existing script (always runs on full path)
    if _FIND_UNUSED.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(_FIND_UNUSED), "--path", str(path), "--format", "json"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                raw = json.loads(result.stdout)
                files_analyzed = raw.get("files_analyzed", 0)
                for sym in raw.get("unused_symbols", []):
                    sym_file = sym.get("file", "")
                    # In incremental mode, filter to changed files only
                    if files is not None:
                        changed_names = {f.name for f in files}
                        if Path(sym_file).name not in changed_names:
                            continue
                    violations.append({
                        "principle": "YAGNI",
                        "file": sym_file,
                        "line": sym.get("line", 0),
                        "severity": "high" if sym.get("confidence") == "high" else "medium",
                        "message": f"Unused {sym.get('type', 'symbol')}: {sym.get('name', '?')}",
                        "suggestion": "Remove dead code to reduce maintenance burden",
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass

    # Part 2: Ollama speculative feature scan
    if check_ollama_available(model):
        if files is not None:
            source_files = [f for f in files if f.suffix in {e for exts in _LANG_EXTENSIONS.values() for e in exts}]
        else:
            exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
            source_files = discover_files(path, exts)
            source_files = [f for f in source_files
                            if not any(m in f.name.lower() for m in _TEST_MARKERS)]
        if not files_analyzed:
            files_analyzed = len(source_files)

        for item in analyze_files_parallel(source_files, language, model, _PROMPT, agents=agents, no_cache=no_cache):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            violations.append({
                "principle": "YAGNI",
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "medium"),
                "message": f"Speculative [{item.get('pattern', '?')}]: {item.get('violation', '')}",
                "suggestion": item.get("suggestion", ""),
            })

    return {
        "principle": "YAGNI",
        "success": True,
        "violations": violations,
        "files_analyzed": files_analyzed,
        "duration_ms": int((time.time() - start) * 1000),
    }
