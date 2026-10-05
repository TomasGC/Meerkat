#!/usr/bin/env python3
"""Tests for safe_read_context.py"""

from pathlib import Path

import pytest
from cli.safe_read_context import read_architecture, read_kanban, read_rules, safe_read_context
from lib.file_utils import read_file_safe

# Add parent directory to path for imports
