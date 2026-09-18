#!/usr/bin/env python3
"""Shared driver for hybrid checkers — mechanical pattern scan then AI deep scan.

A hybrid checker supplies a per-language pattern table and a prompt name; this
module handles file discovery, the mechanical pass, prompt-slot injection of the
mechanical findings, the AI pass, and proximity deduplication between the two.
"""

import re
import sys
import time
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.ai.model_utils import analyze_files_parallel, check_server_available
from lib.config import language_config
from lib.engine.dedup import drop_near_duplicates, format_known_findings
from lib.engine.discovery import _LANG_EXTENSIONS, _TEST_MARKERS, discover_files

_ALL_EXTENSIONS = set(language_config.extensions())

# (pattern, message, severity, suggestion)
Rule = tuple[re.Pattern, str, str, str]


def resolve_language(file: Path, language: str) -> str:
    """Map a file to its language, resolving the "mixed" placeholder by name or extension."""
    if language_config.matches_filename("dockerfile", file.name):
        return "dockerfile"
    if language != "mixed":
        return language
    return language_config.language_for_extension(file.suffix) or "unknown"


def select_files(path: Path, language: str, files: list | None) -> list[Path]:
    """Return the files to analyze, honouring an explicit incremental file list."""
    if files is not None:
        return [f for f in files if f.suffix in _ALL_EXTENSIONS]
    exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
    discovered = discover_files(path, exts)
    return [f for f in discovered if not any(m in f.name.lower() for m in _TEST_MARKERS)]


def scan_patterns(
    file: Path,
    root: Path,
    language: str,
    principle: str,
    rules: dict[str, list[Rule]],
) -> list[dict]:
    """Apply the language's rules line by line and return checker-contract violations."""
    applicable = rules.get(language, []) + rules.get("*", [])
    if not applicable:
        return []
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    violations = []
    for i, line in enumerate(content.splitlines(), 1):
        for pattern, message, severity, suggestion in applicable:
            if pattern.search(line):
                violations.append({
                    "principle": principle,
                    "file": filename,
                    "line": i,
                    "severity": severity,
                    "message": message,
                    "suggestion": suggestion,
                })
    return violations


def run_hybrid(
    path: Path,
    language: str,
    principle: str,
    prompt: str,
    rules: dict[str, list[Rule]],
    prompts_dir: Path,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
    ai_type_key: str = "issue_type",
    default_severity: str = "medium",
) -> dict:
    """Run the mechanical pass, then the AI pass informed by its results."""
    start = time.time()
    source_files = select_files(path, language, files)

    violations: list[dict] = []
    per_file: dict[Path, list[dict]] = {}
    for file in source_files:
        per_file[file] = scan_patterns(file, path, resolve_language(file, language), principle, rules)
        violations.extend(per_file[file])

    if check_server_available(role) and source_files:
        extra_slots = {
            f: {"known_findings": format_known_findings(per_file.get(f, []))}
            for f in source_files
        }
        ai_violations = []
        for item in analyze_files_parallel(source_files, language, role, prompt,
                                           prompts_dir=prompts_dir, agents=agents,
                                           no_cache=no_cache, extra_slots=extra_slots):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            ai_violations.append({
                "principle": principle,
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", default_severity),
                "message": f"[{item.get(ai_type_key, '?')}]: {item.get('description', '')}",
                "suggestion": item.get("fix", ""),
            })
        violations.extend(drop_near_duplicates(ai_violations, violations))

    return {
        "principle": principle,
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
