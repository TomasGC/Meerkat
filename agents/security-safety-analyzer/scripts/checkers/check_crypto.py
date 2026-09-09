#!/usr/bin/env python3
"""Cryptographic failure checker (OWASP A02) — weak algorithms, weak randomness, disabled TLS."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.hybrid import run_hybrid

_PRINCIPLE = "Crypto"
_PROMPT = "crypto"

_WEAK_HASH = "Weak hash algorithm — MD5 and SHA-1 are broken for security use"
_WEAK_HASH_FIX = "Use SHA-256 or better; for passwords use bcrypt, scrypt or Argon2"
_WEAK_RANDOM = "General-purpose RNG used where a value must be unguessable"
_WEAK_RANDOM_FIX = "Use a cryptographically secure RNG (secrets, RandomNumberGenerator, crypto.randomBytes)"
_NO_TLS_VERIFY = "TLS certificate validation disabled — traffic can be intercepted"
_NO_TLS_VERIFY_FIX = "Keep verification on; trust the internal CA instead of skipping the check"

_RULES = {
    "python": [
        (re.compile(r'hashlib\.(?:md5|sha1)\s*\('), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'(?i)\brandom\.(?:random|randint|choice|randrange)\s*\('), _WEAK_RANDOM, "medium", _WEAK_RANDOM_FIX),
        (re.compile(r'verify\s*=\s*False'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'ssl\._create_unverified_context'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'(?i)(?:password|secret|token|signature)\w*\s*==\s'),
         "Secret compared with == — vulnerable to timing attacks", "medium",
         "Use hmac.compare_digest for constant-time comparison"),
    ],
    "csharp": [
        (re.compile(r'\b(?:MD5|SHA1)\.Create\s*\('), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'\b(?:MD5CryptoServiceProvider|SHA1Managed)\b'), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'\b(?:DES|TripleDES|RC2)CryptoServiceProvider\b'),
         "Obsolete symmetric cipher — DES, 3DES and RC2 are no longer safe", "high",
         "Use AES with an authenticated mode such as GCM"),
        (re.compile(r'CipherMode\.ECB'),
         "ECB mode leaks plaintext structure", "high",
         "Use CBC with a random IV, or preferably GCM"),
        (re.compile(r'\bnew\s+Random\s*\('), _WEAK_RANDOM, "medium", _WEAK_RANDOM_FIX),
        (re.compile(r'ServerCertificateValidationCallback\s*=|ServerCertificateCustomValidationCallback\s*='),
         _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
    ],
    "go": [
        (re.compile(r'"crypto/(?:md5|sha1)"'), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'\b(?:md5|sha1)\.(?:New|Sum)\s*\('), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'"math/rand"|\brand\.(?:Intn|Int31|Float64)\s*\('), _WEAK_RANDOM, "medium", _WEAK_RANDOM_FIX),
        (re.compile(r'InsecureSkipVerify\s*:\s*true'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
    ],
    "javascript": [
        (re.compile(r'createHash\s*\(\s*["\'](?:md5|sha1)["\']'), _WEAK_HASH, "high", _WEAK_HASH_FIX),
        (re.compile(r'Math\.random\s*\('), _WEAK_RANDOM, "medium", _WEAK_RANDOM_FIX),
        (re.compile(r'rejectUnauthorized\s*:\s*false'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'NODE_TLS_REJECT_UNAUTHORIZED\s*[=:]\s*["\']?0'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
    ],
    "powershell": [
        (re.compile(r'-SkipCertificateCheck'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'\[System\.Net\.ServicePointManager\]::ServerCertificateValidationCallback'),
         _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'Get-FileHash\s+.*-Algorithm\s+(?:MD5|SHA1)\b'), _WEAK_HASH, "medium", _WEAK_HASH_FIX),
    ],
    "bash": [
        (re.compile(r'\bcurl\s+[^|\n]*(?:-k\b|--insecure)'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'--no-check-certificate'), _NO_TLS_VERIFY, "high", _NO_TLS_VERIFY_FIX),
        (re.compile(r'\bmd5sum\b'),
         "MD5 used for integrity verification — collisions are cheap", "medium",
         "Use sha256sum instead"),
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
        ai_type_key="weakness_type", default_severity="high",
    )
