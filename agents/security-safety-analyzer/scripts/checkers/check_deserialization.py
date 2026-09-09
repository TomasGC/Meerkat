#!/usr/bin/env python3
"""Deserialization checker (OWASP A08) — unsafe object graphs and XML entity expansion."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.hybrid import run_hybrid

_PRINCIPLE = "Deserialization"
_PROMPT = "deserialization"

_UNSAFE_DESER = "Untrusted data deserialized into arbitrary objects — remote code execution risk"
_UNSAFE_DESER_FIX = "Use a data-only format (JSON) with an explicit schema, or restrict allowed types"
_XXE = "XML parser resolves external entities — XXE risk"
_XXE_FIX = "Disable DTD processing and external entity resolution on the parser"

_RULES = {
    "python": [
        (re.compile(r'\bpickle\.loads?\s*\(|\bcPickle\.loads?\s*\('), _UNSAFE_DESER, "high", _UNSAFE_DESER_FIX),
        (re.compile(r'\bmarshal\.loads?\s*\('), _UNSAFE_DESER, "high", _UNSAFE_DESER_FIX),
        (re.compile(r'\bshelve\.open\s*\('), _UNSAFE_DESER, "medium", _UNSAFE_DESER_FIX),
        (re.compile(r'yaml\.load\s*\((?![^)]*Safe)'),
         "yaml.load without SafeLoader constructs arbitrary Python objects", "high",
         "Use yaml.safe_load, or pass Loader=yaml.SafeLoader"),
        (re.compile(r'etree\.(?:parse|fromstring)\s*\((?![^)]*resolve_entities\s*=\s*False)'), _XXE, "medium", _XXE_FIX),
    ],
    "csharp": [
        (re.compile(r'\bBinaryFormatter\b|\bLosFormatter\b|\bSoapFormatter\b|\bNetDataContractSerializer\b'),
         _UNSAFE_DESER, "high", _UNSAFE_DESER_FIX),
        (re.compile(r'TypeNameHandling\s*=\s*TypeNameHandling\.(?!None)'),
         "Newtonsoft TypeNameHandling lets the payload choose the type — RCE risk", "high",
         "Set TypeNameHandling.None, or bind types with a SerializationBinder"),
        (re.compile(r'DtdProcessing\s*=\s*DtdProcessing\.Parse'), _XXE, "high", _XXE_FIX),
        (re.compile(r'XmlResolver\s*=\s*new\s+Xml(?:Url|Secure)Resolver'), _XXE, "medium", _XXE_FIX),
    ],
    "javascript": [
        (re.compile(r'require\s*\(\s*["\']node-serialize["\']|\bunserialize\s*\('),
         _UNSAFE_DESER, "high", _UNSAFE_DESER_FIX),
        (re.compile(r'\beval\s*\(\s*(?:JSON|body|req\.|data\b)'),
         "Payload evaluated as code instead of parsed", "high",
         "Use JSON.parse and validate the result"),
        (re.compile(r'noent\s*:\s*true|noEnt\s*:\s*true'), _XXE, "high", _XXE_FIX),
    ],
    "powershell": [
        (re.compile(r'Import-Clixml\s'), _UNSAFE_DESER, "medium", _UNSAFE_DESER_FIX),
        (re.compile(r'\[System\.Management\.Automation\.PSSerializer\]::Deserialize'),
         _UNSAFE_DESER, "medium", _UNSAFE_DESER_FIX),
    ],
    "go": [
        (re.compile(r'\bgob\.NewDecoder\s*\('), _UNSAFE_DESER, "medium", _UNSAFE_DESER_FIX),
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
        ai_type_key="issue_type", default_severity="high",
    )
