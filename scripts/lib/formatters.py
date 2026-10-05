#!/usr/bin/env python3
"""
Output formatting utilities.

Consistent formatting for JSON and YAML outputs.
"""

import json
from typing import Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON.

    Args:
        data: Data to format
        indent: Indentation spaces

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


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
