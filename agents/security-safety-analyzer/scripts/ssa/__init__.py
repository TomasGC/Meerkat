"""Security Safety Analyzer — the one importable package of this agent (#21)."""

import sys
from pathlib import Path

# The shared library (scripts/lib) of this checkout, not of ~/.claude (#2). Every module of the
# package is imported through it, so this is the only place the package touches sys.path.
_SHARED = Path(__file__).resolve().parents[4] / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
