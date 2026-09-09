#!/usr/bin/env python3
"""Security misconfiguration checker (OWASP A05) — permissive defaults and debug settings."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.hybrid import run_hybrid

_PRINCIPLE = "Misconfiguration"
_PROMPT = "misconfiguration"

_DEBUG_EXPOSED = "Debug output enabled — leaks stack traces and configuration"
_DEBUG_FIX = "Guard behind an environment check and disable it outside development"

_RULES = {
    "csharp": [
        (re.compile(r'\.AllowAnyOrigin\s*\('),
         "CORS allows any origin", "high",
         "Whitelist the specific origins with WithOrigins"),
        (re.compile(r'\.SetIsOriginAllowed\s*\(\s*_?\s*=>\s*true'),
         "CORS origin predicate always returns true", "high",
         "Validate the origin against an allow list"),
        (re.compile(r'RequireHttpsMetadata\s*=\s*false'),
         "Token metadata fetched over plain HTTP", "high",
         "Set RequireHttpsMetadata = true"),
        (re.compile(r'UseDeveloperExceptionPage\s*\('), _DEBUG_EXPOSED, "medium", _DEBUG_FIX),
        (re.compile(r'CookieOptions[^;]*(?:Secure\s*=\s*false|HttpOnly\s*=\s*false)'),
         "Cookie missing Secure or HttpOnly", "high",
         "Set Secure = true and HttpOnly = true"),
        (re.compile(r'\[AllowAnonymous\]'),
         "Endpoint explicitly opts out of authentication", "medium",
         "Confirm the endpoint is meant to be public"),
    ],
    "python": [
        (re.compile(r'^\s*DEBUG\s*=\s*True'), _DEBUG_EXPOSED, "high", _DEBUG_FIX),
        (re.compile(r'ALLOWED_HOSTS\s*=\s*\[\s*["\']\*["\']'),
         "ALLOWED_HOSTS accepts any host — enables host header attacks", "high",
         "List the served hostnames explicitly"),
        (re.compile(r'\.run\s*\([^)]*debug\s*=\s*True'), _DEBUG_EXPOSED, "high", _DEBUG_FIX),
        (re.compile(r'host\s*=\s*["\']0\.0\.0\.0["\']'),
         "Service bound to every interface", "medium",
         "Bind to localhost or a specific interface behind the proxy"),
        (re.compile(r'CORS_ORIGIN_ALLOW_ALL\s*=\s*True|origins\s*=\s*\[\s*["\']\*["\']'),
         "CORS allows any origin", "high",
         "Whitelist the specific origins"),
    ],
    "javascript": [
        (re.compile(r'cors\s*\(\s*\{\s*origin\s*:\s*["\']\*["\']|cors\s*\(\s*\)'),
         "CORS allows any origin", "high",
         "Pass an explicit origin allow list to cors()"),
        (re.compile(r'\bcookie\s*\(\s*[^)]*secure\s*:\s*false|httpOnly\s*:\s*false'),
         "Cookie missing Secure or HttpOnly", "high",
         "Set secure: true and httpOnly: true"),
        (re.compile(r'NODE_ENV\s*[=:]\s*["\']?development'), _DEBUG_EXPOSED, "low", _DEBUG_FIX),
    ],
    "yaml": [
        (re.compile(r'privileged\s*:\s*true'),
         "Container runs privileged — full host access", "high",
         "Drop privileged and grant only the capabilities needed"),
        (re.compile(r'readOnlyRootFilesystem\s*:\s*false'),
         "Container root filesystem is writable", "medium",
         "Set readOnlyRootFilesystem: true and mount writable volumes explicitly"),
        (re.compile(r'hostNetwork\s*:\s*true|hostPID\s*:\s*true|hostIPC\s*:\s*true'),
         "Container shares a host namespace — breaks isolation", "high",
         "Remove the host namespace sharing"),
        (re.compile(r'runAsUser\s*:\s*0|runAsNonRoot\s*:\s*false'),
         "Container runs as root", "high",
         "Set runAsNonRoot: true and a non-zero runAsUser"),
        (re.compile(r'allowPrivilegeEscalation\s*:\s*true'),
         "Privilege escalation allowed inside the container", "high",
         "Set allowPrivilegeEscalation: false"),
    ],
    "dockerfile": [
        (re.compile(r'^\s*FROM\s+\S+:latest'),
         "Base image pinned to latest — builds are not reproducible", "medium",
         "Pin an explicit version or digest"),
        (re.compile(r'--no-check-certificate|--insecure'),
         "Certificate validation skipped during build", "high",
         "Fetch over HTTPS with validation enabled"),
        (re.compile(r'^\s*RUN\s+.*\b(?:curl|wget)\b[^|]*\|\s*(?:ba)?sh'),
         "Build pipes a downloaded script into a shell", "high",
         "Download, verify the checksum, then execute"),
    ],
    "bash": [
        (re.compile(r'\bchmod\s+(?:-R\s+)?777\b'),
         "World-writable permissions", "high",
         "Grant the narrowest permissions the process needs"),
        (re.compile(r'\bumask\s+000\b'),
         "umask 000 makes new files world-writable", "high",
         "Use a restrictive umask such as 027"),
    ],
    "powershell": [
        (re.compile(r'Set-ExecutionPolicy\s+(?:Bypass|Unrestricted)'),
         "Execution policy relaxed — unsigned scripts run silently", "high",
         "Use RemoteSigned or sign the scripts"),
        (re.compile(r'-Force\s+.*-Recurse.*Set-Acl|icacls\s+.*\/grant\s+Everyone'),
         "Everyone granted access to a filesystem object", "high",
         "Grant access to a specific service principal"),
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
        ai_type_key="misconfig_type", default_severity="medium",
    )
