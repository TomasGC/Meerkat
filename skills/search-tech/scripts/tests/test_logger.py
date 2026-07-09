#!/usr/bin/env python3
"""Tests for common.logger module."""

import pytest
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logger import setup_logger, MetricsCollector


class TestSetupLogger:
    """Test setup_logger function."""

    def test_default_logger(self):
        """Test logger with default settings."""
        logger = setup_logger("test")

        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1

    def test_verbose_logger(self):
        """Test logger with verbose flag."""
        logger = setup_logger("test", verbose=True)

        assert logger.level == logging.INFO

    def test_debug_logger(self):
        """Test logger with debug flag."""
        logger = setup_logger("test", debug=True)

        assert logger.level == logging.DEBUG

    def test_logger_name(self):
        """Test logger name is set correctly."""
        logger = setup_logger("my_module")

        assert logger.name == "my_module"

    def test_logger_removes_existing_handlers(self):
        """Test that existing handlers are removed."""
        logger = logging.getLogger("test_handler_removal")
        logger.addHandler(logging.NullHandler())

        assert len(logger.handlers) == 1

        setup_logger("test_handler_removal")

        # Should have exactly 1 handler (the new one)
        assert len(logger.handlers) == 1


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_initial_metrics_are_zero(self):
        """Test metrics start at zero."""
        metrics = MetricsCollector()

        assert metrics.get('api_calls') == 0
        assert metrics.get('cache_hits') == 0
        assert metrics.get('errors') == 0

    def test_increment_metric(self):
        """Test incrementing a metric."""
        metrics = MetricsCollector()

        metrics.increment('api_calls')
        assert metrics.get('api_calls') == 1

        metrics.increment('api_calls', 5)
        assert metrics.get('api_calls') == 6

    def test_increment_unknown_metric(self):
        """Test incrementing unknown metric does nothing."""
        metrics = MetricsCollector()

        metrics.increment('unknown_metric')
        assert metrics.get('unknown_metric') == 0

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        metrics = MetricsCollector()

        metrics.increment('api_calls', 10)
        metrics.increment('errors', 3)

        assert metrics.get('api_calls') == 10
        assert metrics.get('errors') == 3

        metrics.reset()

        assert metrics.get('api_calls') == 0
        assert metrics.get('errors') == 0

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        metrics = MetricsCollector()

        metrics.increment('cache_hits', 7)
        metrics.increment('cache_misses', 3)

        summary = metrics.summary()

        assert summary['cache_hit_rate_percent'] == 70.0

    def test_cache_hit_rate_with_no_cache_access(self):
        """Test cache hit rate when no cache access."""
        metrics = MetricsCollector()

        summary = metrics.summary()

        assert summary['cache_hit_rate_percent'] == 0

    def test_metrics_summary(self):
        """Test full metrics summary."""
        metrics = MetricsCollector()

        metrics.increment('api_calls', 5)
        metrics.increment('cache_hits', 3)
        metrics.increment('cache_misses', 2)
        metrics.increment('errors', 1)
        metrics.increment('total_results', 10)

        summary = metrics.summary()

        assert summary['api_calls'] == 5
        assert summary['cache_hits'] == 3
        assert summary['cache_misses'] == 2
        assert summary['errors'] == 1
        assert summary['total_results'] == 10
        assert summary['cache_hit_rate_percent'] == 60.0

    def test_metrics_string_representation(self):
        """Test metrics __str__ method."""
        metrics = MetricsCollector()

        metrics.increment('api_calls', 3)
        metrics.increment('cache_hits', 2)
        metrics.increment('cache_misses', 1)
        metrics.increment('total_results', 5)

        metrics_str = str(metrics)

        assert 'API calls: 3' in metrics_str
        assert 'Cache hits: 2/3' in metrics_str
        assert 'Results: 5' in metrics_str
