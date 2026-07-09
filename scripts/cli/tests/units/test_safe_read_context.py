#!/usr/bin/env python3
"""Tests for safe_read_context.py"""

import pytest
from pathlib import Path

# Add parent directory to path for imports

from cli.safe_read_context import (
    read_kanban,
    read_architecture,
    read_rules,
    safe_read_context
)
from common.file_utils import read_file_safe
