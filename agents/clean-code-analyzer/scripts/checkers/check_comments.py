#!/usr/bin/env python3
"""Comments checker — TODO/FIXME, commented-out code, explain-WHAT comments."""

import re
import time
from pathlib import Path

from common.file_utils import _SKIP_DIRS, _ALL_EXTENSIONS, _HASH_COMMENT_EXTS, is_hash_comment_file

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


def _check_file(file: Path, root: Path) -> list[dict]:
    violations = []
    rel = str(file.relative_to(root) if file.is_relative_to(root) else file)
    is_hash_comment = is_hash_comment_file(file)
    todo_re = _TODO_RE if is_hash_comment else _TODO_RE_SLASH
    code_re = _CODE_IN_COMMENT_PY if is_hash_comment else _CODE_IN_COMMENT_C
    what_re = _WHAT_VERBS if is_hash_comment else _WHAT_VERBS_SLASH

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


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    start = time.time()
    violations = []

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

    for file in source_files:
        violations.extend(_check_file(file, path))

    return {
        "principle": "Comments",
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
