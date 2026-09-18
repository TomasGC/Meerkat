#!/usr/bin/env python3
"""Thin shim over the shared engine discovery module."""

import subprocess  # noqa: F401 — re-exported so common.file_utils.subprocess patches reach the real module
import sys
from pathlib import Path

_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from lib.config import language_config  # noqa: F401
from lib.engine.discovery import (  # noqa: F401
    _ALL_EXTENSIONS,
    _DISCOVERY_CACHE,
    _LANG_EXTENSIONS,
    _SKIP_DIRS,
    _TEST_MARKERS,
    detect_language,
    discover_files,
    get_branch_files,
    get_changed_files,
    get_staged_files,
    read_file_safe,
)
