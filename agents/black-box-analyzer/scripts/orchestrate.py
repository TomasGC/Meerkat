#!/usr/bin/env python3
"""Black-Box Analyzer entry point — the code lives in bba/orchestrate.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bba.orchestrate import main

if __name__ == "__main__":
    main()
