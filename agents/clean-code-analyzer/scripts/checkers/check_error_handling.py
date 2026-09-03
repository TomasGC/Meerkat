#!/usr/bin/env python3
"""Error handling checker — AST-based for Python, grep for others."""

import ast
import re
import time
from pathlib import Path

_GREP_PATTERNS = {
    "csharp": [
        (re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "Empty catch block"),
        (re.compile(r"catch\s*\([^)]*\)\s*\{[^}]*//\s*TODO"), "Caught but not handled (TODO)"),
    ],
    "typescript": [
        (re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "Empty catch block"),
        (re.compile(r"catch\s*\([^)]*\)\s*\{[^}]*\}"), None),  # handled below
    ],
    "javascript": [
        (re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "Empty catch block"),
    ],
    "go": [
        (re.compile(r"if err != nil \{\s*\}"), "Empty error check block"),
        (re.compile(r"_ = \w+\.(\w+)\("), "Error explicitly discarded with _"),
    ],
    "powershell": [
        (re.compile(r"catch\s*\{\s*\}"), "Empty catch block"),
        (re.compile(r"-ErrorAction\s+SilentlyContinue"), "Errors silently ignored with -ErrorAction SilentlyContinue"),
    ],
    "bash": [
        (re.compile(r"\|\|\s*true\b"), "Error swallowed with || true"),
        (re.compile(r"\|\|\s*:\s*$"), "Error swallowed with || :"),
        (re.compile(r"2\s*>/dev/null"), "Stderr silently discarded with 2>/dev/null"),
    ],
}

from common.file_utils import _LANG_EXTENSIONS as _LANG_EXTS


def _check_python_file(file: Path, root: Path) -> list[dict]:
    violations = []
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file))
    except (OSError, SyntaxError):
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue

        body = node.body
        # Empty except body (only Pass or Ellipsis)
        if all(isinstance(stmt, (ast.Pass, ast.Expr)) for stmt in body):
            if all(
                isinstance(getattr(stmt, "value", None), ast.Constant)
                for stmt in body
                if isinstance(stmt, ast.Expr)
            ):
                exc_type = ast.unparse(node.type) if node.type else "Exception"
                violations.append({
                    "principle": "ErrorHandling",
                    "file": str(file.relative_to(root) if file.is_relative_to(root) else file),
                    "line": node.lineno,
                    "severity": "high",
                    "message": f"Swallowed exception: bare `except {exc_type}: pass`",
                    "suggestion": "Log the exception or re-raise; never silently swallow",
                })
                continue

        # Catch-all without re-raise or logging
        if node.type is None:
            has_raise = any(isinstance(s, ast.Raise) for s in ast.walk(node))
            has_log = any(
                isinstance(s, ast.Call) and isinstance(getattr(s.func, "attr", None), str)
                and s.func.attr in ("error", "warning", "exception", "critical", "info", "debug")
                for s in ast.walk(node)
            )
            if not has_raise and not has_log:
                violations.append({
                    "principle": "ErrorHandling",
                    "file": str(file.relative_to(root) if file.is_relative_to(root) else file),
                    "line": node.lineno,
                    "severity": "high",
                    "message": "Bare `except:` catches all exceptions without logging or re-raising",
                    "suggestion": "Catch specific exceptions; log or re-raise",
                })
            continue

        # Generic Exception catch — check if specific is possible
        if node.type and isinstance(node.type, ast.Name) and node.type.id == "Exception":
            has_raise = any(isinstance(s, ast.Raise) for s in ast.walk(node))
            has_log = any(
                isinstance(s, ast.Call) and isinstance(getattr(s.func, "attr", None), str)
                and s.func.attr in ("error", "warning", "exception", "critical")
                for s in ast.walk(node)
            )
            if not has_raise and not has_log:
                violations.append({
                    "principle": "ErrorHandling",
                    "file": str(file.relative_to(root) if file.is_relative_to(root) else file),
                    "line": node.lineno,
                    "severity": "medium",
                    "message": "Caught `Exception` without logging or re-raising — possible silent failure",
                    "suggestion": "Log the exception or re-raise; prefer specific exception types",
                })

    return violations


def _check_non_python(file: Path, root: Path, language: str) -> list[dict]:
    violations = []
    patterns = _GREP_PATTERNS.get(language, [])
    if not patterns:
        return []

    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
    except OSError:
        return []

    for pattern, message in patterns:
        if message is None:
            continue
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                violations.append({
                    "principle": "ErrorHandling",
                    "file": str(file.relative_to(root) if file.is_relative_to(root) else file),
                    "line": i,
                    "severity": "high",
                    "message": message,
                    "suggestion": "Handle or log the exception; never silently swallow errors",
                })

    return violations


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    start = time.time()
    violations = []
    source_files: list[Path] = []

    if files is not None:
        source_files = list(files)
    elif path.is_file():
        source_files = [path]
    else:
        for lang, exts in _LANG_EXTS.items():
            for ext in exts:
                source_files.extend(p for p in path.rglob(f"*{ext}")
                             if not any(part in {".git", "node_modules", "__pycache__", ".venv", "venv",
                                                 "bin", "obj", "dist", "vendor", "build", "out"} for part in p.parts))
    for file in source_files:
        if file.suffix == ".py":
            violations.extend(_check_python_file(file, path))
        else:
            lang = next((l for l, exts in _LANG_EXTS.items() if file.suffix in exts), "unknown")
            violations.extend(_check_non_python(file, path, lang))

    return {
        "principle": "ErrorHandling",
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
