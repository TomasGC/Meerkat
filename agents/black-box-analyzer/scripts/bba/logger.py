#!/usr/bin/env python3
"""
Logging utilities for black-box-analyzer scripts.

Provides structured logging with different verbosity levels and performance metrics.
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
        self.metrics = {
            'files_analyzed': 0,
            'entry_points_found': 0,
            'tests_parsed': 0,
            'scenarios_generated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
        }

    def increment(self, metric: str, amount: int = 1):
        """Increment a metric counter."""
        if metric in self.metrics:
            self.metrics[metric] += amount

    def get(self, metric: str) -> int:
        """Get current metric value."""
        return self.metrics.get(metric, 0)

    def reset(self):
        """Reset all metrics to zero."""
        for key in self.metrics:
            self.metrics[key] = 0

    def summary(self) -> dict:
        """Get metrics summary."""
        total_cache = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (
            (self.metrics['cache_hits'] / total_cache * 100)
            if total_cache > 0 else 0
        )

        return {
            **self.metrics,
            'cache_hit_rate_percent': round(cache_hit_rate, 1),
        }

    def __str__(self) -> str:
        """String representation of metrics."""
        summary = self.summary()
        return (
            f"Files: {summary['files_analyzed']}, "
            f"Entry points: {summary['entry_points_found']}, "
            f"Tests: {summary['tests_parsed']}, "
            f"Scenarios: {summary['scenarios_generated']}, "
            f"Cache: {summary['cache_hits']}/{summary['cache_hits'] + summary['cache_misses']} "
            f"({summary['cache_hit_rate_percent']}%), "
            f"Errors: {summary['errors']}"
        )


def get_defaults(logger=None, metrics=None, module_name: str = __name__):
    """
    Get default logger and metrics if not provided.

    Args:
        logger: Logger instance (or None for default)
        metrics: Metrics collector (or None for default)
        module_name: Module name for logger (default: __name__)

    Returns:
        Tuple of (logger, metrics)

    Example:
        logger, metrics = get_defaults(logger, metrics, __name__)
    """
    if logger is None:
        logger = setup_logger(module_name)
    if metrics is None:
        metrics = MetricsCollector()
    return logger, metrics
