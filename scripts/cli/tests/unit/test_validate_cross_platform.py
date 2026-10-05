#!/usr/bin/env python3
"""Tests for validate_cross_platform.py"""

from pathlib import Path

import pytest
from cli.validate_cross_platform import (
    check_environment_variables,
    check_file_naming_conventions,
    check_hardcoded_paths,
    check_path_api_usage,
    check_platform_specific_cmdlets,
    validate_script_cross_platform,
)

# Add parent directory to path for imports
