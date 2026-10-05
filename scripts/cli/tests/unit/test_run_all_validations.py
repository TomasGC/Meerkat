#!/usr/bin/env python3
"""Tests for run_all_validations.py"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.run_all_validations import get_validation_script_path, invoke_validation_script, run_all_validations

# Add parent directory to path for imports
