#!/usr/bin/env python3
"""
Search metrics, plus the shared logger.

Logging itself (`ColoredFormatter`, `setup_logger`) comes from `lib.logger`, the
one implementation (#22). `MetricsCollector` stays here: its counters are the
search summary printed by every search script with `--verbose`.
"""


from lib.logger import ColoredFormatter, setup_logger  # noqa: E402,F401 — re-exported


class MetricsCollector:
    """Collect and report performance metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'retries': 0,
            'total_results': 0,
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
            f"API calls: {summary['api_calls']}, "
            f"Cache hits: {summary['cache_hits']}/{summary['cache_hits'] + summary['cache_misses']} "
            f"({summary['cache_hit_rate_percent']}%), "
            f"Errors: {summary['errors']}, "
            f"Results: {summary['total_results']}"
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
