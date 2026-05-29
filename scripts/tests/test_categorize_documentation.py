#!/usr/bin/env python3
"""Tests for categorize_documentation.py"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.categorize_documentation import (
    categorize_file,
    categorize_documentation
)
