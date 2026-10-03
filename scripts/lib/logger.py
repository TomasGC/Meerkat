#!/usr/bin/env python3
"""
Logging utilities for Claude scripts.

Provides structured, colored logging with different verbosity levels.
The one logging implementation: search-tech imports it too (#22).
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Add colors to log output for terminal visibility."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    verbose: bool = False,
    debug: bool = False
) -> logging.Logger:
    """
    Setup logger with appropriate formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level
        verbose: Enable verbose output
        debug: Enable debug output (overrides level)

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Determine level
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO

    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with colors
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Format
    if debug:
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        formatter = ColoredFormatter('%(levelname)s - %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
