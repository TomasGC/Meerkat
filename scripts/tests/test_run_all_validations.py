#!/usr/bin/env python3
"""Tests for run_all_validations.py"""

import pytest
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.run_all_validations import (
    get_validation_script_path,
    invoke_validation_script,
    run_all_validations
)
