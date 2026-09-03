#!/usr/bin/env python3
"""Law of Demeter checker — grep/AST for deep method/property chains."""

import re
import time
from pathlib import Path

from common.file_utils import _SKIP_DIRS, _ALL_EXTENSIONS

# Method chain depth > 2: matches a.b().c().d() style
_CHAIN_RE = re.compile(r"\w+(?:\.\w+\(\)(?:\.\w+)*){2,}")

# Property access depth > 2: a.b.c.d (not in import/using statements)
_PROP_CHAIN_RE = re.compile(r"(?<!import\s)(?<!from\s)(?<!using\s)\b\w+(?:\.\w+){3,}\b")

# Exempt patterns (builder/fluent/linq/pandas/assertions)
_EXEMPT_RE = re.compile(
    r"(?:\.Where\(|\.Select\(|\.OrderBy\(|\.GroupBy\(|\.ToList\(|\.ToArray\("
    r"|\.should\.|\.assert\.|\.expect\(|\.then\(|\.catch\(|\.finally\("
    r"|\.pipe\(|\.map\(|\.filter\(|\.reduce\("
    r"|logging\.\w+\.\w+|self\.logger\.\w+|console\.\w+)",
    re.IGNORECASE,
)


def _check_file(file: Path, root: Path) -> list[dict]:
    violations = []
    rel = str(file.relative_to(root) if file.is_relative_to(root) else file)

    try:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "*", "/*")):
            continue

        # Skip exempt fluent/builder patterns
        if _EXEMPT_RE.search(line):
            continue

        # Method chain violations
        for m in _CHAIN_RE.finditer(line):
            chain = m.group(0)
            depth = chain.count("().")
            if depth >= 2:
                violations.append({
                    "principle": "LawOfDemeter",
                    "file": rel,
                    "line": i,
                    "severity": "medium" if depth == 2 else "high",
                    "message": f"Method chain depth {depth + 1}: `{chain[:60]}`",
                    "suggestion": "Introduce intermediate local variables or delegate to the direct collaborator",
                })

        # Deep property access
        for m in _PROP_CHAIN_RE.finditer(line):
            chain = m.group(0)
            depth = chain.count(".")
            if depth >= 3 and "." in chain:
                # Skip common false positives
                if any(skip in chain for skip in ("self.", "this.", "__", "os.path", "sys.argv")):
                    continue
                violations.append({
                    "principle": "LawOfDemeter",
                    "file": rel,
                    "line": i,
                    "severity": "low",
                    "message": f"Deep property access ({depth} levels): `{chain[:60]}`",
                    "suggestion": "Access only direct collaborators; expose needed data through the immediate object",
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
        "principle": "LawOfDemeter",
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
