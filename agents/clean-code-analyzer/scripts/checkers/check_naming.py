#!/usr/bin/env python3
"""Naming checker — magic numbers, magic strings, bad names (pure grep/regex)."""

import ast
import re
import time
from pathlib import Path

from common.file_utils import _SKIP_DIRS, _ALL_EXTENSIONS
from common.file_utils import _TEST_MARKERS

# Numbers that are generally acceptable as literals
_OK_NUMBERS = {"0", "1", "2", "-1", "100", "200", "201", "204", "400", "401",
               "403", "404", "422", "500", "1000"}

_MAGIC_NUMBER_RE = re.compile(r"(?<!['\"\w])(\b\d{2,}\b)(?!['\"\w])")
_CONST_ASSIGNMENT_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}\s*=")
_MAGIC_STRING_CONDITION_RE = re.compile(r'(?:==|!=|in\s)\s*["\']([^"\']{3,})["\']')
_SINGLE_LETTER_VAR_RE = re.compile(r"\b([a-zA-Z])\s*=\s*(?![\s]*for\b)")
_LOOP_VAR_RE = re.compile(r"for\s+([a-zA-Z])\s+in\b")

# Methods that yield a bool are expected to read as a question
_BOOL_NAME_PREFIXES = ("is_", "has_", "can_", "should_")
_BOOL_EXEMPT_NAMES = frozenset({"run", "execute", "start", "stop", "init", "setup"})

_ALLOWED_SHORT = {"id", "db", "ok", "err", "ctx", "req", "res", "ip", "os", "io",
                  "fn", "cb", "dt", "ts", "pk", "fk", "ui", "ux", "vm", "fs"}



def _is_test_file(path: Path) -> bool:
    return any(marker in path.name.lower() for marker in _TEST_MARKERS)


def _returns_bool(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the annotation says bool, or every returned value is a bool literal."""
    annotation = node.returns
    if isinstance(annotation, ast.Name) and annotation.id == "bool":
        return True
    if annotation is not None:
        # Annotated as something else — trust the annotation
        return False

    returned = [
        n.value for n in ast.walk(node)
        if isinstance(n, ast.Return) and n.value is not None
    ]
    if not returned:
        return False
    return all(
        isinstance(v, ast.Constant) and isinstance(v.value, bool)
        for v in returned
    )


def _bool_method_violations(source: str, rel: str) -> list[dict]:
    """Flag bool-returning methods whose names don't read as a question.

    Return type drives this, not the name alone: the earlier regex matched every
    method lacking an is_/has_/can_/should_ prefix, so ordinary getters such as
    `get_active_users` were reported as boolean-naming violations.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (node.args.args and node.args.args[0].arg == "self"):
                continue
            name = node.name
            if name.startswith(_BOOL_NAME_PREFIXES) or name in _BOOL_EXEMPT_NAMES:
                continue
            if not _returns_bool(node):
                continue
            violations.append({
                "principle": "Naming",
                "file": rel,
                "line": node.lineno,
                "severity": "low",
                "message": f"Method `{name}` returns bool but name doesn't start with is/has/can/should",
                "suggestion": f"Rename to `is_{name}`, `has_{name}`, or `can_{name}`",
            })
    return violations


def _check_file(file: Path, root: Path) -> list[dict]:
    violations = []
    is_test = _is_test_file(file)

    try:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    rel = str(file.relative_to(root) if file.is_relative_to(root) else file)
    loop_vars: set[str] = set()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments and blank lines
        if not stripped or stripped.startswith(("#", "//", "*", "/*", "'")):
            continue

        # Collect loop variables (exempt from single-letter check)
        for m in _LOOP_VAR_RE.finditer(line):
            loop_vars.add(m.group(1))

        if not is_test:
            # Skip ALL_CAPS = <value> lines (constant definitions, not magic numbers)
            is_const_def = bool(_CONST_ASSIGNMENT_RE.match(stripped))
            # Magic numbers (strip range(...) calls first to avoid false positives)
            line_no_range = re.sub(r'\brange\s*\([^)]*\)', '', line)
            for m in _MAGIC_NUMBER_RE.finditer(line_no_range):
                num = m.group(1)
                if num not in _OK_NUMBERS and not is_const_def:
                    violations.append({
                        "principle": "Naming",
                        "file": rel,
                        "line": i,
                        "severity": "medium",
                        "message": f"Magic number: {num}",
                        "suggestion": f"Extract to a named constant (e.g. MAX_RETRIES = {num})",
                    })

            # Magic strings in conditions
            for m in _MAGIC_STRING_CONDITION_RE.finditer(line):
                val = m.group(1)
                violations.append({
                    "principle": "Naming",
                    "file": rel,
                    "line": i,
                    "severity": "medium",
                    "message": f'Magic string in condition: "{val}"',
                    "suggestion": f'Extract to a named constant (e.g. STATUS_ACTIVE = "{val}")',
                })

        # Single-letter variables outside loops
        for m in _SINGLE_LETTER_VAR_RE.finditer(line):
            var = m.group(1).lower()
            if var not in loop_vars and var not in ("_", "x", "y", "z"):
                violations.append({
                    "principle": "Naming",
                    "file": rel,
                    "line": i,
                    "severity": "low",
                    "message": f"Single-letter variable: `{m.group(1)}`",
                    "suggestion": "Use a descriptive name that conveys intent",
                })

    if file.suffix == ".py":
        violations.extend(_bool_method_violations("\n".join(lines), rel))

    return violations


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    start = time.time()
    violations = []
    source_files: list[Path]

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
    files = source_files

    for file in source_files:
        violations.extend(_check_file(file, path))

    return {
        "principle": "Naming",
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
