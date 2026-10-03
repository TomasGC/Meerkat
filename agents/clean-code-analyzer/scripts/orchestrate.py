#!/usr/bin/env python3
"""Clean Code Analyzer entry point — the code lives in cca/orchestrate.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cca.orchestrate import main

if __name__ == "__main__":
    main()
