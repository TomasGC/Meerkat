#!/usr/bin/env python3
"""Tests for categorize_documentation.py"""

import pytest
from pathlib import Path

# Add parent directory to path for imports

from cli.categorize_documentation import (
    categorize_file,
    categorize_documentation
)
