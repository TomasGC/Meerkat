#!/usr/bin/env python3
"""Resource leak checker — undisposed handles, blocked async calls, missing cleanup."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.hybrid import run_hybrid

_PRINCIPLE = "ResourceLeak"
_PROMPT = "resource_leaks"

_UNDISPOSED = "Disposable resource created without a using block or explicit disposal"
_UNDISPOSED_FIX = "Wrap the resource in a using statement, or dispose it in a finally block"

_RULES = {
    "csharp": [
        # `using` can sit far from `new` (`using var c = new SqlConnection(...)`),
        # so the guard is a line-start lookahead rather than a lookbehind.
        (re.compile(r'^\s*(?!(?:await\s+)?using\b)'
                    r'.*\bnew\s+(?:SqlConnection|SqlCommand|StreamReader|StreamWriter'
                    r'|FileStream|MemoryStream|HttpClient|SqlDataReader|TcpClient)\s*\('),
         _UNDISPOSED, "high", _UNDISPOSED_FIX),
        (re.compile(r'\.Result\b'),
         "Blocking on a task with .Result — deadlocks on a captured context", "high",
         "Await the task instead"),
        (re.compile(r'\.Wait\s*\(\s*\)'),
         "Blocking on a task with .Wait() — deadlocks on a captured context", "high",
         "Await the task instead"),
        (re.compile(r'\basync\s+void\b'),
         "async void cannot be awaited — exceptions escape and the caller cannot observe completion", "high",
         "Return Task, except for genuine event handlers"),
        (re.compile(r'GetAwaiter\s*\(\s*\)\s*\.GetResult\s*\(\s*\)'),
         "Synchronous wait on an awaitable — deadlock risk", "high",
         "Await the task instead"),
    ],
    "python": [
        (re.compile(r'(?<!with )\b(?:open|socket\.socket)\s*\([^)]*\)\s*$'),
         "File or socket opened outside a with block", "medium",
         "Use a with statement so the handle closes on every path"),
        (re.compile(r'ThreadPoolExecutor\s*\((?![^)]*\)\s*as\b)'),
         "Executor created without a context manager — worker threads may outlive the call", "medium",
         "Use `with ThreadPoolExecutor(...) as pool:` or call shutdown explicitly"),
        # Statement starts with the call, so the returned task is discarded.
        (re.compile(r'^\s*asyncio\.create_task\s*\('),
         "Task created without keeping a reference — it can be garbage collected mid-flight", "medium",
         "Keep the task in a variable and await or gather it"),
    ],
    # Go leaks (missing `defer Close()`, `defer` inside a loop) need multi-line
    # context, so they are left to the AI layer rather than guessed line by line.
    "javascript": [
        (re.compile(r'^\s*(?!.*\bawait\b)(?!.*\breturn\b)(?!.*\.then\b)(?!.*\bcatch\b)'
                    r'\s*\w+(?:\.\w+)*\.(?:save|update|delete|insert|write|flush)(?:Async)?\s*\('),
         "Promise-returning call is not awaited — errors are swallowed and ordering is undefined", "medium",
         "Await the call or chain .catch()"),
        (re.compile(r'createReadStream\s*\(|createWriteStream\s*\('),
         "Stream created — confirm it is closed or piped to completion", "low",
         "Handle the close and error events, or use pipeline()"),
        (re.compile(r'setInterval\s*\((?![^)]*clearInterval)'),
         "Interval started without a matching clearInterval — timer leak", "medium",
         "Keep the handle and clear it during teardown"),
    ],
    "powershell": [
        (re.compile(r'New-Object\s+System\.IO\.(?:StreamReader|StreamWriter|FileStream)'),
         _UNDISPOSED, "medium", "Call .Dispose() in a finally block"),
        (re.compile(r'\[System\.Data\.SqlClient\.SqlConnection\]::new|New-Object\s+System\.Data\.SqlClient\.SqlConnection'),
         _UNDISPOSED, "medium", "Call .Dispose() in a finally block"),
    ],
}

_RULES["typescript"] = _RULES["javascript"]


def run(
    path: Path,
    language: str,
    files: list | None = None,
    agents: int = 1,
    no_cache: bool = False,
    role: str = "analyzer",
) -> dict:
    return run_hybrid(
        path, language, _PRINCIPLE, _PROMPT, _RULES,
        files=files, agents=agents, no_cache=no_cache, role=role,
        ai_type_key="leak_type", default_severity="medium",
    )
