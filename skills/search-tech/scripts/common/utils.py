#!/usr/bin/env python3
"""
Utility functions for search scripts.

Common helpers to reduce code duplication.
"""

from functools import wraps
import time
from typing import Callable, Any


def retry_on_timeout(max_retries: int = 3, delay: float = 2.0):
    """
    Decorator for retrying API calls on timeout.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay in seconds between retries

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_timeout(max_retries=3, delay=2)
        def fetch_api():
            response = requests.get(url, timeout=10)
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import requests  # Import here to avoid circular dependency

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    else:
                        # Last attempt failed, re-raise
                        raise
        return wrapper
    return decorator
