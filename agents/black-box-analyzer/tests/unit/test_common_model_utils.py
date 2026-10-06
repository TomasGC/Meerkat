#!/usr/bin/env python3
"""Tests for common/model_utils.py — unit tests (extract_json_*, run_prompt logic, PROMPTS_DIR)"""

import json
from unittest.mock import patch

import pytest

from bba.model_utils import (
    PROMPTS_DIR,
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
    result = run_prompt("nonexistent", tmp_path)
    assert result is None
    assert "not found" in capsys.readouterr().err


def test_run_prompt_formats_and_calls_model(tmp_path):
    prompt_file = tmp_path / "greet.prompt"
    prompt_file.write_text("Hello {subject}!", encoding="utf-8")

    captured = {}

    def fake_call_model(prompt, role="fast", timeout=120):
        captured["prompt"] = prompt
        captured["role"] = role
        return "response"

    with patch("lib.ai.model_utils.call_model", side_effect=fake_call_model):
        result = run_prompt("greet", tmp_path, role="fast", timeout=60, subject="World")

    assert result == "response"
    assert captured["prompt"] == "Hello World!"
    assert captured["role"] == "fast"


def test_run_prompt_missing_kwarg_raises(tmp_path):
    prompt_file = tmp_path / "tpl.prompt"
    prompt_file.write_text("Hello {subject} and {other}!", encoding="utf-8")

    with patch("lib.ai.model_utils.call_model", return_value="ok"):
        with pytest.raises(KeyError):
            run_prompt("tpl", tmp_path, subject="World")


def test_run_prompt_propagates_none_from_call_model(tmp_path):
    prompt_file = tmp_path / "p.prompt"
    prompt_file.write_text("hi {x}", encoding="utf-8")

    with patch("lib.ai.model_utils.call_model", return_value=None):
        assert run_prompt("p", tmp_path, x="v") is None


def test_prompts_dir_name_is_local():
    assert PROMPTS_DIR.name == "local"


def test_prompts_dir_parent_is_prompts():
    assert PROMPTS_DIR.parent.name == "prompts"


# ── CACHE binding: every analyze_* call gets BBA's own model cache ────────────


def test_model_cache_round_trips_through_bba_cache(tmp_path):
    from bba import model_utils

    source = tmp_path / "a.py"
    source.write_text("x = 1")
    model_utils.CACHE.set(source, "unit_gaps", [{"line": 1}])
    assert model_utils.CACHE.get(source, "unit_gaps") == [{"line": 1}]


@pytest.mark.parametrize("name", ["analyze_file_with_model", "analyze_files_parallel"])
def test_sync_analyze_wrappers_pass_bba_cache(name):
    from bba import model_utils

    with patch(f"lib.ai.model_utils.{name}", return_value=["r"]) as target:
        assert getattr(model_utils, name)("f", "python") == ["r"]
    assert target.call_args.kwargs["cache"] is model_utils.CACHE


def test_sync_analyze_wrapper_keeps_caller_cache():
    from bba import model_utils

    with patch("lib.ai.model_utils.analyze_files_parallel", return_value=[]) as target:
        model_utils.analyze_files_parallel("f", cache=None)
    assert target.call_args.kwargs["cache"] is None


def test_async_analyze_wrapper_passes_bba_cache():
    import asyncio

    from bba import model_utils

    async def fake(*_args, **kwargs):
        return kwargs["cache"]

    with patch("lib.ai.model_utils.analyze_files_async", side_effect=fake):
        assert asyncio.run(model_utils.analyze_files_async("f")) is model_utils.CACHE
