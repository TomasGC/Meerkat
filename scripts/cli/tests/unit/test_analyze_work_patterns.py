#!/usr/bin/env python3
"""Tests for analyze_work_patterns.py"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.analyze_work_patterns import (
    analyze_work_patterns,
    get_commit_hashes,
    get_technology_from_extension,
    matches_file_pattern,
)

# Add parent directory to path for imports
