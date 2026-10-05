#!/usr/bin/env python3
"""Thin shim over the shared engine dedup logic."""

from lib.engine.dedup import _NO_FINDINGS_TEXT  # noqa: F401
from lib.engine.dedup import (  # noqa: F401
    drop_near_duplicates,
    format_known_findings,
)
