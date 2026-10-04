#!/usr/bin/env python3
"""Tests for validate_cross_platform.py"""

import pytest
from pathlib import Path

# Add parent directory to path for imports

from cli.validate_cross_platform import (
    check_hardcoded_paths,
    check_path_api_usage,
    check_platform_specific_cmdlets,
    check_file_naming_conventions,
    check_environment_variables,
    validate_script_cross_platform
)
