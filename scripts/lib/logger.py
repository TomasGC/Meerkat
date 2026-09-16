#!/usr/bin/env python3
"""
Logging utilities for Claude scripts.

Provides structured logging with different verbosity levels and performance metrics.
DRY pattern from black-box-analyzer and search-tech.
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


class MetricsCollector:
    """Collect and report performance metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {}

    def track(self, metric: str, value: int | dict | None = None):
        """
        Track a metric.

        Args:
            metric: Metric name
            value: Metric value (int for counter, dict for metadata)
        """
        if value is None:
            value = 1

        if isinstance(value, int):
            # Counter metric
            self.metrics[metric] = self.metrics.get(metric, 0) + value
        elif isinstance(value, dict):
            # Metadata metric
            if metric not in self.metrics:
                self.metrics[metric] = []
            self.metrics[metric].append(value)

    def get(self, metric: str) -> int | list | None:
        """Get current metric value."""
        return self.metrics.get(metric)

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()

    def summary(self) -> dict:
        """Get metrics summary."""
        return self.metrics.copy()

    def __str__(self) -> str:
        """String representation of metrics."""
        parts = []
        for key, value in self.metrics.items():
            if isinstance(value, list):
                parts.append(f"{key}: {len(value)} items")
            else:
                parts.append(f"{key}: {value}")
        return ", ".join(parts) if parts else "No metrics"


def get_defaults(logger=None, metrics=None, module_name: str | None = None):
    """
    Get default logger and metrics if not provided.

    DRY helper to reduce initialization boilerplate.

    Args:
        logger: Logger instance (or None for default)
        metrics: Metrics collector (or None for default)
        module_name: Module name for logger (default: root logger)

    Returns:
        Tuple of (logger, metrics)

    Example:
        logger, metrics = get_defaults(logger, metrics, __name__)
        # Or simplified:
        logger, metrics = get_defaults(__name__)
    """
    if logger is None:
        if module_name is None:
            logger = setup_logger("root")
        elif isinstance(module_name, str):
            logger = setup_logger(module_name)
        else:
            logger = module_name  # Already a logger

    if metrics is None:
        metrics = MetricsCollector()

    return logger, metrics
