#!/usr/bin/env python3
"""
Output formatting utilities.

Consistent formatting for JSON and YAML outputs.
"""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def _to_json(value: Any) -> Any:
    """Serialize what json can't: dataclass instances, as their fields."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON.

    Args:
        data: Data to format; dataclass instances are written as their fields
        indent: Indentation spaces

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False, default=_to_json)


def format_yaml(data: Any) -> str:
    """
    Format data as YAML.

    Args:
        data: Data to format

    Returns:
        YAML string
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML not installed. Run: pip install pyyaml")

    return yaml.dump(data, default_flow_style=False, allow_unicode=True)
