#!/usr/bin/env python3
"""Tests for common/ollama_utils.py — unit tests (extract_json_*, run_prompt logic, _PROMPTS_DIR path)"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.ollama_utils import (
    extract_json_array,
    extract_json_object,
    run_prompt,
)

def test_extract_json_array_empty_string():
    assert extract_json_array("") is None

def test_extract_json_array_none_input():
    assert extract_json_array(None) is None

def test_extract_json_array_direct():
    assert extract_json_array('[{"a": 1}]') == [{"a": 1}]

def test_extract_json_array_wrapped_in_prose():
    text = 'Here is the result:\n[{"method": "Foo"}]\nDone.'
    result = extract_json_array(text)
    assert result == [{"method": "Foo"}]

def test_extract_json_array_not_a_list():
    assert extract_json_array('{"key": "value"}') is None

def test_extract_json_array_malformed():
    assert extract_json_array("[not valid json]") is None

def test_extract_json_array_empty_array():
    assert extract_json_array("[]") == []

def test_extract_json_array_nested():
    data = [{"branches": [{"condition": "null"}]}]
    assert extract_json_array(json.dumps(data)) == data

def test_extract_json_object_empty_string():
    assert extract_json_object("") is None

def test_extract_json_object_direct():
    assert extract_json_object('{"key": "value"}') == {"key": "value"}

def test_extract_json_object_wrapped_in_prose():
    text = 'Result: {"score": 42} end'
    assert extract_json_object(text) == {"score": 42}

def test_extract_json_object_not_a_dict():
    assert extract_json_object("[1, 2, 3]") is None

def test_extract_json_object_malformed():
    assert extract_json_object("{not valid}") is None

def test_run_prompt_missing_file_returns_none(tmp_path, capsys):
    with patch("common.ollama_utils._PROMPTS_DIR", tmp_path):
        result = run_prompt("nonexistent")
    assert result is None
    assert "not found" in capsys.readouterr().err

def test_run_prompt_formats_and_calls_ollama(tmp_path):
    prompt_file = tmp_path / "greet.prompt"
    prompt_file.write_text("Hello {subject}!", encoding="utf-8")

    captured = {}

    def fake_call_ollama(prompt, model, timeout):
        captured["prompt"] = prompt
        captured["model"] = model
        return "response"

    with patch("common.ollama_utils._PROMPTS_DIR", tmp_path), \
         patch("common.ollama_utils.call_ollama", side_effect=fake_call_ollama):
        result = run_prompt("greet", model="my-model", timeout=60, subject="World")

    assert result == "response"
    assert captured["prompt"] == "Hello World!"
    assert captured["model"] == "my-model"

def test_run_prompt_missing_kwarg_raises(tmp_path):
    prompt_file = tmp_path / "tpl.prompt"
    prompt_file.write_text("Hello {subject} and {other}!", encoding="utf-8")

    with patch("common.ollama_utils._PROMPTS_DIR", tmp_path), \
         patch("common.ollama_utils.call_ollama", return_value="ok"):
        with pytest.raises(KeyError):
            run_prompt("tpl", subject="World")

def test_run_prompt_propagates_none_from_call_ollama(tmp_path):
    prompt_file = tmp_path / "p.prompt"
    prompt_file.write_text("hi {x}", encoding="utf-8")

    with patch("common.ollama_utils._PROMPTS_DIR", tmp_path), \
         patch("common.ollama_utils.call_ollama", return_value=None):
        assert run_prompt("p", x="v") is None

def test_prompts_dir_name_is_ollama():
    from common import ollama_utils
    assert ollama_utils._PROMPTS_DIR.name == "ollama"

def test_prompts_dir_parent_is_prompts():
    from common import ollama_utils
    assert ollama_utils._PROMPTS_DIR.parent.name == "prompts"
