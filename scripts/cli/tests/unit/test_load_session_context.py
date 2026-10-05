#!/usr/bin/env python3
"""Tests for load_session_context.py"""

from pathlib import Path
from unittest.mock import patch

import pytest
from cli.load_session_context import get_issue_from_branch, load_kanban_entry, load_session_context

# Add parent directory to path for imports
