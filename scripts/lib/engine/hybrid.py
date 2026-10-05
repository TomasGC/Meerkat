#!/usr/bin/env python3
"""Shared driver for hybrid checkers — mechanical pattern scan then AI deep scan.

A hybrid checker supplies a per-language pattern table and a prompt name; this
module handles file discovery, the mechanical pass, prompt-slot injection of the
mechanical findings, the AI pass, and proximity deduplication between the two.
"""

import re
import time
from pathlib import Path
from typing import Callable

from lib.ai.model_utils import ModelCache, analyze_files_parallel, check_server_available
from lib.config import language_config
from lib.engine.cache import get_cached, set_cached
from lib.engine.dedup import drop_near_duplicates, format_known_findings
from lib.engine.discovery import _LANG_EXTENSIONS, discover_files, is_test_file

_ALL_EXTENSIONS = set(language_config.extensions())

# (pattern, message, severity, suggestion)
Rule = tuple[re.Pattern, str, str, str]


def resolve_language(file: Path, language: str) -> str:
    """Map a file to its language, resolving the "mixed" placeholder by name or extension."""
    if language_config.matches_filename("dockerfile", file.name):
        return "dockerfile"
    if language != "mixed":
        return language
    return language_config.language_for_file(file) or "unknown"


def select_files(path: Path, language: str, files: list | None) -> list[Path]:
    """Return the files to analyze, honouring an explicit incremental file list."""
    if files is not None:
        # By language, not suffix: a Dockerfile has none. Tests are skipped in both
        # modes, so an incremental run analyzes the same kind of files as a full one.
        return [f for f in files if language_config.language_for_file(f) is not None and not is_test_file(f)]
    exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
    return [f for f in discover_files(path, exts) if not is_test_file(f)]


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
                violations.append(
                    {
                        "principle": principle,
                        "file": filename,
                        "line": i,
                        "severity": severity,
                        "message": message,
                        "suggestion": suggestion,
                    }
                )
    return violations


def run_hybrid(
    path: Path,
    language: str,
    principle: str,
    prompt: str | None,
    rules: dict[str, list[Rule]],
    prompts_dir: Path | None = None,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
    ai_type_key: str = "issue_type",
    default_severity: str = "medium",
    mechanical_fn: Callable[[Path, list | None], tuple[list[dict], int] | dict] | None = None,
    format_ai_violation: Callable[[dict, str], dict] | None = None,
    cache_dir: Path | None = None,
    cache_ttl_days: int = 7,
    ai_filter: Callable[[Path], bool] | None = None,
    model_cache: ModelCache | None = None,
) -> dict:
    """Run the mechanical pass, then the AI pass informed by its results.

    `mechanical_fn(path, files) -> (violations, files_analyzed)` replaces the
    internal regex scan when the checker's mechanical layer isn't a per-line
    rule table (external subprocess, AST walk, stateful multi-pattern scan).
    It may instead return a full checker-result dict (with "success") to
    short-circuit on a hard failure — the AI pass is skipped in that case.

    `format_ai_violation(item, rel_path) -> violation_dict` replaces the
    default description/fix/principle formatting when a checker's AI prompt
    returns differently-shaped items (e.g. a dynamic principle tag).

    `prompt=None` skips the AI pass entirely — for checkers with no AI layer.

    `model_cache` is handed to the AI client as-is: an agent's own per-file cache
    of raw model answers, for agents that do not use `cache_dir`.

    `ai_filter(file) -> bool` narrows the AI pass to the files it accepts, for a
    prompt that only makes sense on some of them (a test-gap prompt cannot see
    the tests, so it only runs on files the mechanical pass found untested).

    `cache_dir` enables a per-file cache of the raw AI items, keyed by file
    content hash and `(prompt, role, agents)`. Only misses reach the model;
    hits and fresh items go through the same formatting and reconciliation.
    `no_cache=True` bypasses it. With `cache_dir=None` nothing is cached here
    and the result carries no cache counters.
    """
    start = time.time()
    use_cache = cache_dir is not None and not no_cache
    cache_key = f"{prompt}__{role}__a{agents}"
    cache_hits = 0
    cache_total = 0

    per_file: dict[Path, list[dict]] = {}
    if mechanical_fn is not None:
        mech_result = mechanical_fn(path, files)
        if isinstance(mech_result, dict):
            mech_result["principle"] = principle
            mech_result["duration_ms"] = int((time.time() - start) * 1000)
            return mech_result
        violations, files_analyzed = mech_result
        violations = list(violations)
    else:
        source_files = select_files(path, language, files)
        violations = []
        for file in source_files:
            per_file[file] = scan_patterns(file, path, resolve_language(file, language), principle, rules)
            violations.extend(per_file[file])
        files_analyzed = len(source_files)

    if prompt is not None:
        source_files = select_files(path, language, files)
        if ai_filter is not None:
            source_files = [f for f in source_files if ai_filter(f)]
        if check_server_available(role) and source_files:
            if mechanical_fn is not None:
                by_file: dict[str, list[dict]] = {}
                for v in violations:
                    by_file.setdefault(v.get("file", ""), []).append(v)

                def known_for(f: Path) -> list[dict]:
                    rel = str(f.relative_to(path) if f.is_relative_to(path) else f)
                    return by_file.get(rel, [])

            else:

                def known_for(f: Path) -> list[dict]:
                    return per_file.get(f, [])

            extra_slots = {f: {"known_findings": format_known_findings(known_for(f))} for f in source_files}
            if use_cache:
                raw_items, misses = _read_ai_cache(cache_dir, source_files, cache_key, cache_ttl_days)
                cache_hits = len(source_files) - len(misses)
                cache_total = len(source_files)
                if misses:
                    failed: set[Path] = set()
                    fresh = analyze_files_parallel(
                        misses,
                        language,
                        role,
                        prompt,
                        prompts_dir=prompts_dir,
                        agents=agents,
                        no_cache=no_cache,
                        extra_slots={f: extra_slots[f] for f in misses},
                        failed=failed,
                        cache=model_cache,
                    )
                    # A failed call is not a clean result: leave it uncached so the next run retries it.
                    _write_ai_cache(cache_dir, [f for f in misses if f not in failed], cache_key, fresh)
                    raw_items.extend(fresh)
            else:
                raw_items = analyze_files_parallel(
                    source_files,
                    language,
                    role,
                    prompt,
                    prompts_dir=prompts_dir,
                    agents=agents,
                    no_cache=no_cache,
                    extra_slots=extra_slots,
                    cache=model_cache,
                )
            ai_violations = []
            for item in raw_items:
                src = Path(item.get("source_file", ""))
                rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
                if format_ai_violation is not None:
                    ai_violations.append(format_ai_violation(item, rel))
                else:
                    ai_violations.append(
                        {
                            "principle": principle,
                            "file": rel,
                            "line": item.get("line", 0),
                            "severity": item.get("severity", default_severity),
                            "message": f"[{item.get(ai_type_key, '?')}]: {item.get('description', '')}",
                            "suggestion": item.get("fix", ""),
                        }
                    )
            violations.extend(drop_near_duplicates(ai_violations, violations))
            if not files_analyzed:
                files_analyzed = len(source_files)

    result = {
        "principle": principle,
        "success": True,
        "violations": violations,
        "files_analyzed": files_analyzed,
        "duration_ms": int((time.time() - start) * 1000),
    }
    if use_cache:
        result["cache_hits"] = cache_hits
        result["cache_total"] = cache_total
    return result


def _read_ai_cache(
    cache_dir: Path,
    source_files: list[Path],
    key: str,
    ttl_days: int,
) -> tuple[list[dict], list[Path]]:
    """Return (raw AI items served from cache, files that missed).

    Cached items carry no path: the entry is keyed by content hash, so the
    current path is re-attached — identical content under a new name must
    report the new name.
    """
    items: list[dict] = []
    misses: list[Path] = []
    for f in source_files:
        cached = get_cached(cache_dir, f, key, ttl_days)
        if cached is None:
            misses.append(f)
            continue
        items.extend({**item, "source_file": str(f), "source_file_name": f.name} for item in cached)
    return items, misses


def _write_ai_cache(cache_dir: Path, misses: list[Path], key: str, fresh: list[dict]) -> None:
    """Store each missed file's raw AI items — `[]` included, so a clean file hits next time."""
    by_file: dict[Path, list[dict]] = {f: [] for f in misses}
    for item in fresh:
        src = Path(item.get("source_file", ""))
        if src in by_file:
            by_file[src].append({k: v for k, v in item.items() if k not in ("source_file", "source_file_name")})
    for f, items in by_file.items():
        set_cached(cache_dir, f, key, items)
