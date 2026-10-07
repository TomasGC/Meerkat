#!/usr/bin/env python3
"""Tests for lib/formatters.py"""

import json
from dataclasses import dataclass
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


@dataclass
class _Inner:
    name: str


@dataclass
class _Outer:
    count: int
    items: list[_Inner]


def test_format_json_writes_dataclasses_as_their_fields():
    text = format_json({"success": True, "value": _Outer(count=1, items=[_Inner("a")])})
    assert json.loads(text) == {"success": True, "value": {"count": 1, "items": [{"name": "a"}]}}


def test_format_json_still_rejects_other_objects():
    with pytest.raises(TypeError, match="object is not JSON serializable"):
        format_json({"value": object()})


def test_format_yaml_round_trips_block_style():
    text = format_yaml({"name": "café", "tools": ["Read", "Bash"]})
    assert "tools:\n- Read\n- Bash\n" in text
    assert yaml.safe_load(text) == {"name": "café", "tools": ["Read", "Bash"]}


def test_format_yaml_without_pyyaml_raises_import_error():
    with patch.object(formatters, "YAML_AVAILABLE", False):
        with pytest.raises(ImportError, match="pip install pyyaml"):
            format_yaml({"a": 1})
