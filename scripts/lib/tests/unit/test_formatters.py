#!/usr/bin/env python3
"""Tests for lib/formatters.py"""

import json
from unittest.mock import patch

import pytest
import yaml

from lib import formatters
from lib.formatters import format_json, format_yaml


def test_format_json_keeps_unicode_and_indent():
    text = format_json({"name": "café", "n": [1]}, indent=4)
    assert '"café"' in text
    assert '\n    "n"' in text
    assert json.loads(text) == {"name": "café", "n": [1]}


def test_format_yaml_round_trips_block_style():
    text = format_yaml({"name": "café", "tools": ["Read", "Bash"]})
    assert "tools:\n- Read\n- Bash\n" in text
    assert yaml.safe_load(text) == {"name": "café", "tools": ["Read", "Bash"]}


def test_format_yaml_without_pyyaml_raises_import_error():
    with patch.object(formatters, "YAML_AVAILABLE", False):
        with pytest.raises(ImportError, match="pip install pyyaml"):
            format_yaml({"a": 1})
