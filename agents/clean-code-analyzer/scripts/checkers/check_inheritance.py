#!/usr/bin/env python3
"""Composition over Inheritance checker — AST for Python, grep for others."""

import ast
import re
import time
from pathlib import Path

from common.file_utils import _SKIP_DIRS, _CLASS_LANG_EXTS

# Grep patterns for non-Python deep inheritance
_EXTENDS_RE = re.compile(r"class\s+\w+\s+extends\s+(\w+)")  # TS/JS/Java
_INHERITS_CS_RE = re.compile(r"class\s+\w+\s*:\s*(\w+)")     # C#

_INTERFACE_MARKERS = re.compile(
    r"(?:Interface|Abstract|Mixin|Base|ABC|Protocol|IService|IRepository)",
    re.IGNORECASE,
)


def _build_inheritance_map_python(files: list[Path]) -> dict[str, list[str]]:
    """Build class → [parent1, parent2, ...] map from Python AST."""
    class_parents: dict[str, list[str]] = {}
    for file in files:
        try:
            source = file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                parents = [
                    (ast.unparse(b) if hasattr(ast, "unparse") else getattr(b, "id", "?"))
                    for b in node.bases
                ]
                class_parents[node.name] = parents
    return class_parents


def _inheritance_depth(cls: str, parents_map: dict[str, list[str]], visited: set) -> int:
    if cls in visited or cls not in parents_map:
        return 0
    visited.add(cls)
    parents = parents_map[cls]
    if not parents:
        return 0
    return 1 + max(_inheritance_depth(p, parents_map, visited) for p in parents)


def _check_python(files: list[Path], root: Path) -> list[dict]:
    violations = []
    parents_map = _build_inheritance_map_python(files)

    for file in files:
        try:
            source = file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue

        rel = str(file.relative_to(root) if file.is_relative_to(root) else file)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            parents = [
                (ast.unparse(b) if hasattr(ast, "unparse") else getattr(b, "id", "?"))
                for b in node.bases
            ]

            # Multiple inheritance (non-mixin/interface)
            if len(node.bases) > 1:
                non_interface = [
                    p for p in parents
                    if not _INTERFACE_MARKERS.search(p)
                ]
                if len(non_interface) > 1:
                    violations.append({
                        "principle": "CompositionOverInheritance",
                        "file": rel,
                        "line": node.lineno,
                        "severity": "medium",
                        "message": f"`{node.name}` uses multiple inheritance: {', '.join(parents)}",
                        "suggestion": "Prefer composition; use mixins only for cross-cutting concerns",
                    })

            # Inheritance depth > 3
            depth = _inheritance_depth(node.name, parents_map, set())
            if depth > 3:
                violations.append({
                    "principle": "CompositionOverInheritance",
                    "file": rel,
                    "line": node.lineno,
                    "severity": "high",
                    "message": f"`{node.name}` inheritance depth {depth} (> 3)",
                    "suggestion": "Flatten the hierarchy; use composition to share behaviour",
                })

    return violations


def _check_non_python(files: list[Path], root: Path) -> list[dict]:
    violations = []
    # Simple heuristic: track class names and their parents via grep
    extends_map: dict[str, str] = {}

    for file in files:
        rel = str(file.relative_to(root) if file.is_relative_to(root) else file)
        try:
            lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines, 1):
            m = _EXTENDS_RE.search(line) or _INHERITS_CS_RE.search(line)
            if m:
                parent = m.group(1)
                # Extract class name
                cls_m = re.search(r"class\s+(\w+)", line)
                if cls_m:
                    cls_name = cls_m.group(1)
                    extends_map[cls_name] = parent

                    # Check depth by walking chain
                    depth = 0
                    current = cls_name
                    visited: set[str] = set()
                    while current in extends_map and current not in visited:
                        visited.add(current)
                        current = extends_map[current]
                        depth += 1

                    if depth > 3:
                        violations.append({
                            "principle": "CompositionOverInheritance",
                            "file": rel,
                            "line": i,
                            "severity": "high",
                            "message": f"`{cls_name}` inheritance depth {depth} (> 3)",
                            "suggestion": "Flatten the hierarchy; use composition to share behaviour",
                        })

    return violations


def run(path: Path, language: str, files: list | None = None, agents: int = 1, no_cache: bool = False) -> dict:
    start = time.time()
    py_files: list[Path] = []
    other_files: list[Path] = []

    if files is not None:
        for f in files:
            if f.suffix == ".py":
                py_files.append(f)
            elif f.suffix in _CLASS_LANG_EXTS:
                other_files.append(f)
    elif path.is_file():
        if path.suffix == ".py":
            py_files = [path]
        else:
            other_files = [path]
    else:
        for p in path.rglob("*.py"):
            if not any(part in _SKIP_DIRS for part in p.parts):
                py_files.append(p)
        for ext in _CLASS_LANG_EXTS:
            for p in path.rglob(f"*{ext}"):
                if not any(part in _SKIP_DIRS for part in p.parts):
                    other_files.append(p)

    violations = _check_python(py_files, path) + _check_non_python(other_files, path)

    return {
        "principle": "CompositionOverInheritance",
        "success": True,
        "violations": violations,
        "files_analyzed": len(py_files) + len(other_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
