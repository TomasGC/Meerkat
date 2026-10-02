#!/usr/bin/env python3
"""Comments checker — TODO/FIXME, commented-out code, explain-WHAT comments."""

import re
import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.config import language_config
from lib.engine.discovery import _SKIP_DIRS, _ALL_EXTENSIONS, _HASH_COMMENT_EXTS, is_hash_comment_file
from lib.engine.hybrid import run_hybrid

# SQL is analyzed too (#42): its `--` comments carry the same TODOs and dead code
FILE_KINDS = ("code", "query")

_TODO_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG|NOCOMMIT)\b", re.IGNORECASE)
_TODO_RE_SLASH = re.compile(r"//\s*(TODO|FIXME|HACK|XXX|BUG|NOCOMMIT)\b", re.IGNORECASE)

# Lines that look like code inside comments
_CODE_IN_COMMENT_PY = re.compile(r"#\s*(?:def |class |if |for |while |return |import |from |\w+\s*=\s*\w)")
_CODE_IN_COMMENT_C = re.compile(r"//\s*(?:var |let |const |function |class |if\s*\(|for\s*\(|while\s*\(|\w+\s*=\s*\w)")

# Explain-WHAT heuristic: comment text mirrors the next line
_WHAT_VERBS = re.compile(
    r"#\s*(?:increment|decrement|loop|iterate|check|get|set|call|return|create|delete|update|add|remove|print|log)\b",
    re.IGNORECASE,
)
_WHAT_VERBS_SLASH = re.compile(
    r"//\s*(?:increment|decrement|loop|iterate|check|get|set|call|return|create|delete|update|add|remove|print|log)\b",
    re.IGNORECASE,
)

# `--` comments (comment_style "dash": SQL)
_TODO_RE_DASH = re.compile(r"--\s*(TODO|FIXME|HACK|XXX|BUG|NOCOMMIT)\b", re.IGNORECASE)
_CODE_IN_COMMENT_DASH = re.compile(
    r"--\s*(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|EXEC|CREATE|ALTER|DROP)\b|--\s*SET\s+@?\w+\s*=",
    re.IGNORECASE,
)
_WHAT_VERBS_DASH = re.compile(
    r"--\s*(?:increment|decrement|loop|iterate|check|get|set|call|return|create|delete|update|add|remove|print|log)\b",
    re.IGNORECASE,
)


def _comment_patterns(file: Path) -> tuple[re.Pattern, re.Pattern, re.Pattern]:
    """(todo, commented-out code, explain-WHAT) for the file's comment style."""
    if is_hash_comment_file(file):
        return _TODO_RE, _CODE_IN_COMMENT_PY, _WHAT_VERBS
    language = language_config.language_for_file(file)
    if language and language_config.get_language(language).get("comment_style") == "dash":
        return _TODO_RE_DASH, _CODE_IN_COMMENT_DASH, _WHAT_VERBS_DASH
    return _TODO_RE_SLASH, _CODE_IN_COMMENT_C, _WHAT_VERBS_SLASH


def _check_file(file: Path, root: Path) -> list[dict]:
    violations = []
    rel = str(file.relative_to(root) if file.is_relative_to(root) else file)
    todo_re, code_re, what_re = _comment_patterns(file)

    try:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    consecutive_code_comments = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # TODO/FIXME/HACK detection
        if todo_re.search(stripped):
            m = todo_re.search(stripped)
            tag = m.group(1).upper() if m else "TODO"
            violations.append({
                "principle": "Comments",
                "file": rel,
                "line": i,
                "severity": "low",
                "message": f"{tag} comment — should be a tracked issue",
                "suggestion": "Create a GitHub/issue tracker ticket and remove the comment",
            })

        # Commented-out code detection
        if code_re.search(stripped):
            consecutive_code_comments += 1
            if consecutive_code_comments >= 2:
                violations.append({
                    "principle": "Comments",
                    "file": rel,
                    "line": i - 1,
                    "severity": "medium",
                    "message": "Commented-out code block detected",
                    "suggestion": "Remove dead code; use version control to recover if needed",
                })
                consecutive_code_comments = 0  # reset to avoid duplicate on next line
        else:
            consecutive_code_comments = 0

        # Explain-WHAT comment heuristic
        if what_re.search(stripped):
            violations.append({
                "principle": "Comments",
                "file": rel,
                "line": i,
                "severity": "low",
                "message": "Comment explains WHAT the code does (obvious from code)",
                "suggestion": "Remove or replace with a WHY comment explaining the reason/constraint",
            })

    return violations


def _mechanical(path: Path, files: list | None) -> tuple[list[dict], int]:
    if files is not None:
        source_files = list(files)
    elif path.is_file():
        source_files = [path]
    else:
        source_files = []
        for ext in _ALL_EXTENSIONS:
            source_files.extend(
                p for p in path.rglob(f"*{ext}")
                if not any(part in _SKIP_DIRS for part in p.parts)
            )
    violations = []
    for file in source_files:
        violations.extend(_check_file(file, path))
    return violations, len(source_files)


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    return run_hybrid(path, language, "Comments", None, {}, files=files, mechanical_fn=_mechanical)
