#!/usr/bin/env python3
"""Tests for common/logger.py"""

import logging
from pathlib import Path

import pytest

from common.logger import MetricsCollector, get_defaults, setup_logger

# ── MetricsCollector ──────────────────────────────────────────────────────────

def test_metrics_initial_values():
    m = MetricsCollector()
    for key in ("files_analyzed", "entry_points_found", "tests_parsed",
                "scenarios_generated", "cache_hits", "cache_misses", "errors"):
        assert m.get(key) == 0

def test_metrics_increment():
    m = MetricsCollector()
    m.increment("files_analyzed")
    m.increment("files_analyzed", 4)
    assert m.get("files_analyzed") == 5

def test_metrics_increment_unknown_key_no_crash():
    m = MetricsCollector()
    m.increment("nonexistent_key")  # must not raise
    assert m.get("nonexistent_key") == 0

def test_metrics_reset():
    m = MetricsCollector()
    m.increment("errors", 3)
    m.reset()
    assert m.get("errors") == 0

def test_metrics_summary_cache_hit_rate():
    m = MetricsCollector()
    m.increment("cache_hits", 3)
    m.increment("cache_misses", 1)
    s = m.summary()
    assert s["cache_hit_rate_percent"] == 75.0

def test_metrics_summary_no_cache_activity():
    m = MetricsCollector()
    s = m.summary()
    assert s["cache_hit_rate_percent"] == 0

def test_metrics_str_contains_key_fields():
    m = MetricsCollector()
    m.increment("files_analyzed", 5)
    m.increment("errors", 2)
    s = str(m)
    assert "Files: 5" in s
    assert "Errors: 2" in s

# ── setup_logger ──────────────────────────────────────────────────────────────

def test_setup_logger_returns_logger():
    logger = setup_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"

def test_setup_logger_debug_sets_debug_level():
    logger = setup_logger("test.debug", debug=True)
    assert logger.level == logging.DEBUG

def test_setup_logger_verbose_sets_info():
    logger = setup_logger("test.verbose", verbose=True)
    assert logger.level == logging.INFO

def test_setup_logger_clears_existing_handlers():
    logger = setup_logger("test.handlers")
    setup_logger("test.handlers")  # second call
    assert len(logger.handlers) == 1  # no duplicate handlers

# ── get_defaults ──────────────────────────────────────────────────────────────

def test_get_defaults_creates_both():
    logger, metrics = get_defaults(module_name="test.defaults")
    assert isinstance(logger, logging.Logger)
    assert isinstance(metrics, MetricsCollector)

def test_get_defaults_reuses_provided():
    existing_logger = setup_logger("test.existing")
    existing_metrics = MetricsCollector()
    existing_metrics.increment("files_analyzed", 7)
    logger, metrics = get_defaults(logger=existing_logger, metrics=existing_metrics)
    assert logger is existing_logger
    assert metrics.get("files_analyzed") == 7
