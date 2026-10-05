#!/usr/bin/env python3
"""Shared driver for BBA's test-gap checkers, on top of the engine's hybrid runner.

Mechanical layer: a source file with no test file in the tier is one whole-file
finding. AI layer: on those untested files only — the prompt never sees the
tests, so it cannot judge a file that has some — it names the functions that
most need one. Both layers report on every run; the engine reconciles them.
"""

from pathlib import Path
from typing import Callable

from bba.model_utils import PROMPTS_DIR
from lib.config import language_config
from lib.engine.discovery import discover_files, is_test_file  # noqa: F401 — is_test_file re-exported
from lib.engine.hybrid import run_hybrid


def find_source_files(path: Path, language: str, files: list | None = None) -> list[Path]:
    """Non-test source files of `language`; of any language when it is unknown or mixed."""
    exts = set(language_config.extensions(language))
    pool = discover_files(path) if files is None else files
    return [
        f
        for f in pool
        if (f.suffix in exts if exts else language_config.language_for_file(f) is not None) and not is_test_file(f)
    ]


def find_tier_test_files(path: Path, tier_parts: list[str]) -> list[Path]:
    """Return files whose path contains tier_parts as consecutive segments."""
    n = len(tier_parts)
    result = []
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        parts = list(f.parts)
        if any(parts[i : i + n] == tier_parts for i in range(len(parts) - n + 1)):
            result.append(f)
    return result


def has_test_in_tier(src: Path, tier_test_files: list[Path]) -> bool:
    """True if any tier test file has a stem that contains the source stem."""
    base = src.stem.lower().removeprefix("test_").removesuffix("_test")
    return any(base in tf.stem.lower() for tf in tier_test_files)


def run_gap_checker(
    path: Path,
    language: str,
    *,
    tier: list[str],
    principle: str,
    prompt: str,
    missing_message: str,
    ai_message: Callable[[dict], str],
    files: list | None = None,
    **engine_kwargs,
) -> dict:
    """One tier's gaps: mechanical "no test file" findings plus the AI's per-function ones."""
    tier_tests = find_tier_test_files(path, tier)
    untested: set[Path] = set()

    def mechanical(root: Path, selected: list | None) -> tuple[list[dict], int]:
        sources = find_source_files(root, language, selected)
        violations = []
        for f in sources:
            if has_test_in_tier(f, tier_tests):
                continue
            untested.add(f)
            violations.append(
                {
                    "principle": principle,
                    "file": str(f.relative_to(root) if f.is_relative_to(root) else f),
                    "line": 0,
                    "severity": "medium",
                    "message": missing_message,
                    "suggestion": f"Add tests/{'/'.join(tier)}/test_{f.stem}.py (or equivalent)",
                }
            )
        return violations, len(sources)

    def format_ai(item: dict, rel: str) -> dict:
        return {
            "principle": principle,
            "file": rel,
            "line": item.get("line", 0),
            "severity": item.get("severity", "medium"),
            "message": ai_message(item),
            "suggestion": item.get("test_scenario", ""),
        }

    return run_hybrid(
        path,
        language,
        principle,
        prompt,
        {},
        prompts_dir=PROMPTS_DIR,
        files=files,
        mechanical_fn=mechanical,
        format_ai_violation=format_ai,
        ai_filter=lambda f: f in untested,
        **engine_kwargs,
    )
