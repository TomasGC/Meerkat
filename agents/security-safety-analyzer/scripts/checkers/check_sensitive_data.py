#!/usr/bin/env python3
"""Sensitive data exposure checker (OWASP A09) — secrets in logs and leaked internals."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.hybrid import run_hybrid

_PRINCIPLE = "SensitiveData"
_PROMPT = "sensitive_data"

# Interpolated mid-pattern, so it carries no inline flag: the owning pattern
# opens with (?i) instead — Python rejects a global flag away from position 0.
_SENSITIVE_FIELD = r'(?:password|passwd|secret|token|api_?key|ssn|credit_?card|card_?number|cvv|pin|private_?key)'

_LOGGED_SECRET = "Sensitive field written to a log or console — secrets persist in log storage"
_LOGGED_SECRET_FIX = "Log an identifier or a masked value instead of the secret itself"
_LEAKED_INTERNALS = "Internal error detail returned to the caller — leaks stack layout and paths"
_LEAKED_INTERNALS_FIX = "Log the detail server-side and return a generic error message"

_RULES = {
    "python": [
        (re.compile(rf'(?i)(?:logger|logging|log)\.\w+\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(rf'(?i)\bprint\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'(?:return|jsonify)\s*\([^)]*traceback\.format_exc'),
         _LEAKED_INTERNALS, "high", _LEAKED_INTERNALS_FIX),
        (re.compile(r'\bprint\s*\(\s*traceback\.'),
         _LEAKED_INTERNALS, "medium", _LEAKED_INTERNALS_FIX),
        (re.compile(rf'(?:return|jsonify)\s*\([^)]*\bstr\s*\(\s*e(?:xc|rror)?\s*\)'),
         _LEAKED_INTERNALS, "medium", _LEAKED_INTERNALS_FIX),
    ],
    "csharp": [
        (re.compile(rf'(?i)(?:_logger|logger|Log)\.\w+\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(rf'(?i)Console\.Write(?:Line)?\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'Console\.Write(?:Line)?\s*\(\s*ex\b'),
         _LEAKED_INTERNALS, "medium", _LEAKED_INTERNALS_FIX),
        (re.compile(r'(?:return|Content|Json|BadRequest|StatusCode)\s*\([^)]*ex\.(?:ToString\s*\(|StackTrace)'),
         _LEAKED_INTERNALS, "high", _LEAKED_INTERNALS_FIX),
    ],
    "javascript": [
        (re.compile(rf'(?i)console\.\w+\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(rf'(?i)(?:logger|log)\.\w+\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'res\.(?:send|json)\s*\([^)]*(?:err\.stack|error\.stack)'),
         _LEAKED_INTERNALS, "high", _LEAKED_INTERNALS_FIX),
    ],
    "go": [
        (re.compile(rf'(?i)(?:log|fmt)\.(?:Print|Printf|Println|Fatalf|Errorf)\s*\([^)]*{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'http\.Error\s*\([^,]+,\s*err\.Error\s*\(\s*\)'),
         _LEAKED_INTERNALS, "high", _LEAKED_INTERNALS_FIX),
    ],
    "powershell": [
        (re.compile(rf'(?i)Write-(?:Host|Output|Verbose|Debug)\s+[^\n]*\${_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'Write-(?:Host|Output)\s+\$_\.Exception'),
         _LEAKED_INTERNALS, "medium", _LEAKED_INTERNALS_FIX),
    ],
    "bash": [
        (re.compile(rf'(?i)\becho\s+[^\n|]*\${{?{_SENSITIVE_FIELD}'),
         _LOGGED_SECRET, "high", _LOGGED_SECRET_FIX),
        (re.compile(r'\bset\s+-x\b'),
         "Shell tracing echoes every command, including secrets passed as arguments", "medium",
         "Enable tracing only around code that handles no secrets"),
    ],
    "razor": [
        (re.compile(r'@(?:Model\.)?(?:Exception|ex)\.(?:StackTrace|ToString\s*\()'),
         _LEAKED_INTERNALS, "high", _LEAKED_INTERNALS_FIX),
    ],
    "*": [
        (re.compile(rf'(?i)[?&](?:token|api_?key|password|secret|access_token)='),
         "Credential passed in a URL query string — captured by logs and referrers", "medium",
         "Move the credential into a header or request body"),
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
        ai_type_key="exposure_type", default_severity="high",
    )
