#!/usr/bin/env python3
"""Security checker — grep for secrets/injection + AI deep scan."""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.file_utils import discover_files, _LANG_EXTENSIONS, _TEST_MARKERS
from common.model_utils import analyze_files_parallel, check_server_available, PROMPTS_DIR
from common.dedup import drop_near_duplicates, format_known_findings

_PRINCIPLE = "Security"
_PROMPT = "security"

# Mechanical patterns: (regex, message, severity)
_SECRET_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|secret|api_key|apikey|token|auth_token)\s*=\s*["\'][^"\']{4,}["\']'),
     "Hardcoded secret or credential", "high"),
    (re.compile(r'(?i)(aws_access_key_id|aws_secret|private_key)\s*=\s*["\'][^"\']+["\']'),
     "Hardcoded cloud credential", "high"),
]

# Weaknesses whose syntax is the same in every language
_UNIVERSAL_PATTERNS = [
    (re.compile(r'(?i)["\']alg["\']\s*:\s*["\']none["\']'),
     "JWT header sets alg=none — signature is never verified", "high"),
    (re.compile(r'(?i)[?&](token|api_key|apikey|password|secret|access_token)='),
     "Credential passed in URL query string — leaks through logs and referrers", "medium"),
]

# ReDoS needs two signals on the same line: a regex construct and a nested quantifier.
# Matching the quantifier alone would flag ordinary arithmetic such as `(a + b) * c`.
_REGEX_CONTEXT = re.compile(r're\.(?:compile|match|search|sub|findall)|new RegExp|Regexp?\s*[(.]|-match|=~')
_NESTED_QUANTIFIER = re.compile(r'\([^)]*[+*]\)\s*[+*]')

_INJECTION_PATTERNS = {
    "python": [
        (re.compile(r'execute\s*\(\s*["\'].*%s.*["\']'), "SQL query built with % formatting — SQL injection risk", "high"),
        (re.compile(r'execute\s*\(\s*f["\']'), "SQL query built with f-string — SQL injection risk", "high"),
        (re.compile(r'execute\s*\(\s*["\'].*\+'), "SQL query built with concatenation — SQL injection risk", "high"),
        (re.compile(r'open\s*\(\s*(?:request|input|os\.environ)'), "Path from external input — path traversal risk", "high"),
        (re.compile(r'requests\.(?:get|post|put|patch|delete|head)\s*\(\s*(?:f["\']|request\.|input\(|os\.environ)'),
         "Outbound request to a caller-controlled URL — SSRF risk", "high"),
        (re.compile(r'redirect\s*\(\s*(?:request\.|f["\'])'),
         "Redirect target from external input — open redirect risk", "medium"),
        (re.compile(r'jwt\.decode\s*\([^)]*verify\s*=\s*False'),
         "JWT decoded with verify=False — signature not checked", "high"),
        (re.compile(r'algorithms\s*=\s*\[\s*["\']none["\']'),
         "JWT accepts the none algorithm — signature can be stripped", "high"),
        (re.compile(r'\*\*request\.(?:json|form|data|POST|args)'),
         "Request body splatted into a model — mass assignment risk", "high"),
    ],
    "javascript": [
        (re.compile(r'innerHTML\s*=\s*[^"\'`]'), "innerHTML set from variable — XSS risk", "high"),
        (re.compile(r'eval\s*\('), "eval() with dynamic code — code injection risk", "high"),
        (re.compile(r'fetch\s*\(\s*(?:`|req\.(?:query|body|params))'),
         "Outbound request to a caller-controlled URL — SSRF risk", "high"),
        (re.compile(r'res\.redirect\s*\(\s*req\.'),
         "Redirect target from external input — open redirect risk", "medium"),
        (re.compile(r'\.\.\.req\.(?:body|query|params)'),
         "Request payload spread into a model — mass assignment risk", "high"),
        (re.compile(r'jwt\.verify\s*\([^)]*algorithms\s*:\s*\[\s*["\']none["\']'),
         "JWT accepts the none algorithm — signature can be stripped", "high"),
    ],
    "typescript": [
        (re.compile(r'innerHTML\s*=\s*[^"\'`]'), "innerHTML set from variable — XSS risk", "high"),
        (re.compile(r'eval\s*\('), "eval() with dynamic code — code injection risk", "high"),
        (re.compile(r'fetch\s*\(\s*(?:`|req\.(?:query|body|params))'),
         "Outbound request to a caller-controlled URL — SSRF risk", "high"),
        (re.compile(r'res\.redirect\s*\(\s*req\.'),
         "Redirect target from external input — open redirect risk", "medium"),
        (re.compile(r'\.\.\.req\.(?:body|query|params)'),
         "Request payload spread into a model — mass assignment risk", "high"),
        (re.compile(r'jwt\.verify\s*\([^)]*algorithms\s*:\s*\[\s*["\']none["\']'),
         "JWT accepts the none algorithm — signature can be stripped", "high"),
    ],
    "go": [
        (re.compile(r'Sprintf\s*\(["\'].*SELECT.*\+'), "SQL query built with Sprintf — SQL injection risk", "high"),
        (re.compile(r'http\.(?:Get|Post|Head)\s*\(\s*r\.(?:URL|FormValue|Form)'),
         "Outbound request to a caller-controlled URL — SSRF risk", "high"),
        (re.compile(r'http\.Redirect\s*\([^,]+,\s*[^,]+,\s*r\.'),
         "Redirect target from external input — open redirect risk", "medium"),
    ],
    "csharp": [
        (re.compile(r'string\.Format\s*\(["\'].*SELECT'), "SQL query built with Format — SQL injection risk", "high"),
        (re.compile(r'\$["\'].*SELECT.*\{'), "SQL query built with interpolation — SQL injection risk", "high"),
        (re.compile(r'(?:GetAsync|PostAsync|SendAsync)\s*\(\s*(?:Request\.|\$")'),
         "Outbound request to a caller-controlled URL — SSRF risk", "high"),
        (re.compile(r'return\s+Redirect\s*\(\s*(?:Request\.|\w+Url\b)'),
         "Redirect target from external input — open redirect risk", "medium"),
        (re.compile(r'\bTryUpdateModel(?:Async)?\s*\('),
         "TryUpdateModel binds every posted field — mass assignment risk", "high"),
        (re.compile(r'Validate(?:Issuer|Audience|Lifetime)\s*=\s*false'),
         "JWT validation disabled — tokens accepted without checks", "high"),
        (re.compile(r'RequireSignedTokens\s*=\s*false'),
         "Unsigned JWTs accepted — signature can be stripped", "high"),
    ],
    "razor": [
        (re.compile(r'@Html\.Raw\s*\('), "Html.Raw emits unencoded output — XSS risk", "high"),
        (re.compile(r'innerHTML\s*=\s*[^"\'`]'), "innerHTML set from variable — XSS risk", "high"),
    ],
    "powershell": [
        (re.compile(r'Invoke-Expression|(?<![\w-])iex\s'), "Invoke-Expression runs dynamic code — code injection risk", "high"),
        (re.compile(r'ConvertTo-SecureString\s+.*-AsPlainText'), "Plaintext secret converted to SecureString", "high"),
    ],
    "bash": [
        (re.compile(r'\beval\s+["\']?\$'), "eval on a variable — command injection risk", "high"),
        (re.compile(r'curl\s+[^|]*\|\s*(?:ba)?sh'), "Piping a downloaded script into a shell — remote code execution risk", "high"),
    ],
}


def _mechanical_check(file: Path, root: Path, language: str) -> list[dict]:
    try:
        content = file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    filename = str(file.relative_to(root) if file.is_relative_to(root) else file)
    violations = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        for pattern, message, severity in _SECRET_PATTERNS:
            if pattern.search(line):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": i,
                    "severity": severity,
                    "message": message,
                    "suggestion": "Use environment variables or a secrets manager; never hardcode credentials",
                })

    lang_patterns = _INJECTION_PATTERNS.get(language, []) + _UNIVERSAL_PATTERNS
    for i, line in enumerate(lines, 1):
        for pattern, message, severity in lang_patterns:
            if pattern.search(line):
                violations.append({
                    "principle": _PRINCIPLE,
                    "file": filename,
                    "line": i,
                    "severity": severity,
                    "message": message,
                    "suggestion": "Use parameterized queries or sanitize/escape all external input",
                })

        if _REGEX_CONTEXT.search(line) and _NESTED_QUANTIFIER.search(line):
            violations.append({
                "principle": _PRINCIPLE,
                "file": filename,
                "line": i,
                "severity": "medium",
                "message": "Nested quantifier in regex — catastrophic backtracking (ReDoS) risk",
                "suggestion": "Rewrite the pattern without nested quantifiers, or bound the input length",
            })

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

    if files is not None:
        source_files = [f for f in files if f.suffix in {e for exts in _LANG_EXTENSIONS.values() for e in exts}]
    else:
        exts = _LANG_EXTENSIONS.get(language) if language != "mixed" else None
        source_files = discover_files(path, exts)
        source_files = [f for f in source_files if not any(m in f.name.lower() for m in _TEST_MARKERS)]

    per_file: dict[Path, list[dict]] = {}
    for file in source_files:
        lang = language if language != "mixed" else next(
            (l for l, exts in _LANG_EXTENSIONS.items() if file.suffix in exts), "unknown"
        )
        per_file[file] = _mechanical_check(file, path, lang)
        violations.extend(per_file[file])

    if check_server_available(role) and source_files:
        extra_slots = {
            f: {"known_findings": format_known_findings(per_file.get(f, []))}
            for f in source_files
        }
        ai_violations = []
        for item in analyze_files_parallel(source_files, language, role, _PROMPT,
                                           prompts_dir=PROMPTS_DIR, agents=agents,
                                           no_cache=no_cache, extra_slots=extra_slots):
            src = Path(item.get("source_file", ""))
            rel = str(src.relative_to(path) if src.is_relative_to(path) else src)
            ai_violations.append({
                "principle": _PRINCIPLE,
                "file": rel,
                "line": item.get("line", 0),
                "severity": item.get("severity", "high"),
                "message": f"[{item.get('vulnerability_type', '?')}]: {item.get('description', '')}",
                "suggestion": item.get("fix", ""),
            })
        violations.extend(drop_near_duplicates(ai_violations, violations))

    return {
        "principle": _PRINCIPLE,
        "success": True,
        "violations": violations,
        "files_analyzed": len(source_files),
        "duration_ms": int((time.time() - start) * 1000),
    }
