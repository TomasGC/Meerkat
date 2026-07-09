#!/usr/bin/env python3
"""Tests for analyze_work_patterns.py"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports

from cli.analyze_work_patterns import (
    matches_file_pattern,
    get_technology_from_extension,
    get_commit_hashes,
    analyze_work_patterns
)
