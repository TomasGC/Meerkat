#!/usr/bin/env python3
"""Concurrency checker — pattern-based thread-safety scan plus AI race detection."""

import ast
import re
import time
from pathlib import Path

from ssa.dedup import drop_near_duplicates, format_known_findings
from ssa.hybrid import resolve_language, select_files
from ssa.model_utils import PROMPTS_DIR, analyze_files_parallel, check_server_available

_PRINCIPLE = "Concurrency"
_PROMPT = "concurrency"
# SQL: dirty reads and unguarded multi-statement writes are concurrency bugs too.
FILE_KINDS = ("code", "query")

_PATTERNS = {
    "csharp": [
        # Type part allows spaces so generics such as Dictionary<string, int> match.
        (
            re.compile(
                r"^\s*(?:private|public|internal|protected)?\s*static\s+"
                r"(?!readonly\b|const\b|class\b|void\b)[\w.<>,\[\]?\s]+\s+\w+\s*="
            ),
            "Mutable static field — shared across threads without synchronization",
            "high",
        ),
        (
            re.compile(r"lock\s*\(\s*(?:this|typeof)\b"),
            "Locking on a publicly reachable object — external code can deadlock it",
            "medium",
        ),
    ],
    "go": [
        (
            re.compile(r"\btime\.Sleep\s*\("),
            "Sleep used to order goroutines — race prone; synchronize explicitly",
            "medium",
        ),
    ],
    "python": [
        (re.compile(r"\btime\.sleep\s*\("), "Sleep used to order threads — race prone; synchronize explicitly", "low"),
    ],
    "sql": [
        (
            re.compile(r"(?i)\bWITH\s*\(\s*NOLOCK\s*\)"),
            "NOLOCK reads uncommitted data — dirty, missing or duplicated rows",
            "medium",
        ),
        (
            re.compile(r"(?i)\bSET\s+TRANSACTION\s+ISOLATION\s+LEVEL\s+READ\s+UNCOMMITTED\b"),
            "READ UNCOMMITTED isolation — dirty reads for the whole session",
            "medium",
        ),
    ],
}

# Patterns that only matter when the file actually spawns concurrent work.
_CONCURRENCY_IMPORTS = {
    "python": re.compile(r"\b(?:import\s+threading|from\s+threading|concurrent\.futures|multiprocessing)\b"),
    "powershell": re.compile(r"\b(?:Start-Job|Start-ThreadJob|RunspacePool)\b"),
}

_SHARED_STATE = {
    "python": (re.compile(r"^\s*global\s+\w+"), "Global mutated from a threaded module — needs a lock", "high"),
    "powershell": (
        re.compile(r"\$global:\w+\s*="),
        "Global variable written from a job — needs synchronization",
        "high",
    ),
}

_LOCK_FACTORIES = frozenset({"Lock", "RLock", "Semaphore", "BoundedSemaphore", "Condition"})
_LOCK_NAME_SUFFIX = "lock"
_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_TARGETS_OF = {
    ast.Assign: lambda n: n.targets,
    ast.AugAssign: lambda n: [n.target],
    ast.AnnAssign: lambda n: [n.target],
    ast.Delete: lambda n: n.targets,
}


def _call_name(node: ast.expr) -> str:
    func = node.func if isinstance(node, ast.Call) else node
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _lock_names(tree: ast.Module) -> set[str]:
    """Names bound to a lock factory call anywhere in the module."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if _call_name(node.value) in _LOCK_FACTORIES:
                names.update(_call_name(target) for target in node.targets)
    return names


def _is_lock(expr: ast.expr, lock_names: set[str]) -> bool:
    if isinstance(expr, ast.Call):  # `with threading.Lock():` locks a fresh object: protects nothing
        return False
    name = _call_name(expr)
    return name in lock_names or name.lower().endswith(_LOCK_NAME_SUFFIX)


def _assigned_names(stmt: ast.stmt) -> set[str]:
    targets = _TARGETS_OF.get(type(stmt))
    if targets is None:
        return set()
    return {n.id for target in targets(stmt) for n in ast.walk(target) if isinstance(n, ast.Name)}


def _child_blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    blocks = [getattr(stmt, field, []) for field in ("body", "orelse", "finalbody")]
    blocks.extend(handler.body for handler in getattr(stmt, "handlers", []))
    return blocks


def _unlocked_writes(body: list[ast.stmt], lock_names: set[str], under_lock: bool = False) -> set[str]:
    """Names assigned outside every lock-guarded `with`, not descending into nested scopes."""
    written: set[str] = set()
    for stmt in body:
        if isinstance(stmt, _NESTED_SCOPES):
            continue
        if not under_lock:
            written |= _assigned_names(stmt)
        guarded = under_lock or (
            isinstance(stmt, (ast.With, ast.AsyncWith))
            and any(_is_lock(item.context_expr, lock_names) for item in stmt.items)
        )
        for block in _child_blocks(stmt):
            written |= _unlocked_writes(block, lock_names, guarded)
    return written


def _global_statements(body: list[ast.stmt]) -> list[ast.Global]:
    found: list[ast.Global] = []
    for stmt in body:
        if isinstance(stmt, ast.Global):
            found.append(stmt)
        elif not isinstance(stmt, _NESTED_SCOPES):
            for block in _child_blocks(stmt):
                found.extend(_global_statements(block))
    return found


def _unlocked_global_lines(content: str) -> list[int] | None:
    """Lines of `global` statements whose names are written outside a lock; None if the source doesn't parse."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    lock_names = _lock_names(tree)
    lines: set[int] = set()
    for func in ast.walk(tree):
        if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            written = _unlocked_writes(func.body, lock_names)
            lines.update(g.lineno for g in _global_statements(func.body) if written & set(g.names))
    return sorted(lines)


_GO_GOROUTINE = re.compile(r"\bgo\s+func\s*\(")
_GO_WAITGROUP_ADD = re.compile(r"\.Add\s*\(")


def _mechanical_check(file: Path, root: Path, language: str) -> list[dict]:
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    lines = content.splitlines()
    violations = []

    def add(line_no: int, message: str, severity: str) -> None:
        violations.append(
            {
                "principle": _PRINCIPLE,
                "file": filename,
                "line": line_no,
                "severity": severity,
                "message": message,
                "suggestion": "Protect shared state with a lock or use an immutable/atomic alternative",
            }
        )

    for i, line in enumerate(lines, 1):
        for pattern, message, severity in _PATTERNS.get(language, []):
            if pattern.search(line):
                add(i, message, severity)

    spawns_concurrency = language in _CONCURRENCY_IMPORTS and _CONCURRENCY_IMPORTS[language].search(content)
    if spawns_concurrency:
        pattern, message, severity = _SHARED_STATE[language]
        flagged = _unlocked_global_lines(content) if language == "python" else None
        if flagged is None:
            flagged = [i for i, line in enumerate(lines, 1) if pattern.search(line)]
        for i in flagged:
            add(i, message, severity)

    if language == "go":
        for i, line in enumerate(lines, 1):
            if not _GO_GOROUTINE.search(line):
                continue
            for offset, following in enumerate(lines[i : i + 3], 1):
                if _GO_WAITGROUP_ADD.search(following):
                    add(i + offset, "WaitGroup.Add called inside the goroutine — Wait can return early", "high")

    return violations


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
) -> dict:
    start = time.time()
    violations = []

    source_files = select_files(path, language, files)

    per_file: dict[Path, list[dict]] = {}
    for file in source_files:
        lang = resolve_language(file, language)
        per_file[file] = _mechanical_check(file, path, lang)
        violations.extend(per_file[file])

    if check_server_available(role) and source_files:
        extra_slots = {f: {"known_findings": format_known_findings(per_file.get(f, []))} for f in source_files}
        ai_violations = []
        for item in analyze_files_parallel(
            source_files,
            language,
            role,
            _PROMPT,
            prompts_dir=PROMPTS_DIR,
            agents=agents,
            no_cache=no_cache,
            extra_slots=extra_slots,
        ):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            ai_violations.append(
                {
                    "principle": _PRINCIPLE,
                    "file": rel,
                    "line": item.get("line", 0),
                    "severity": item.get("severity", "high"),
                    "message": f"[{item.get('issue_type', '?')}]: {item.get('description', '')}",
                    "suggestion": item.get("fix", ""),
                }
            )
        violations.extend(drop_near_duplicates(ai_violations, violations))

    return {
        "principle": _PRINCIPLE,
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
