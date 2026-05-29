#!/usr/bin/env python3
"""
Pytest configuration and fixtures for tests.

Handles platform-specific test skipping and shared test utilities.
"""

import sys
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unix: mark test to run only on Unix-like systems"
    )
    config.addinivalue_line(
        "markers", "windows: mark test to run only on Windows"
    )
    config.addinivalue_line(
        "markers", "requires_shellcheck: mark test that requires shellcheck"
    )


def pytest_runtest_setup(item):
    """
    Auto-skip tests based on platform markers.

    Tests marked with @pytest.mark.unix will be skipped on Windows.
    Tests marked with @pytest.mark.windows will be skipped on Unix.
    """
    # Check for unix marker
    if "unix" in item.keywords:
        if sys.platform == "win32":
            pytest.skip("Test requires Unix-like system (Linux/macOS)")

    # Check for windows marker
    if "windows" in item.keywords:
        if sys.platform != "win32":
            pytest.skip("Test requires Windows")

    # Check for linux marker
    if "linux" in item.keywords:
        if not sys.platform.startswith("linux"):
            pytest.skip("Test requires Linux")

    # Check for macos marker
    if "macos" in item.keywords:
        if sys.platform != "darwin":
            pytest.skip("Test requires macOS")
