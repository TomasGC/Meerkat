#!/usr/bin/env python3
"""Tests for load_session_context.py"""

import pytest
from pathlib import Path
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.load_session_context import (
    get_issue_from_branch,
    load_kanban_entry,
    load_session_context
)
