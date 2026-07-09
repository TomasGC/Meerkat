#!/usr/bin/env python3
"""Tests for common/ollama_utils.py — int_real tests (live Ollama required)"""

from pathlib import Path
from unittest.mock import patch

import pytest

from common.ollama_utils import analyze_file_with_ollama, call_ollama, run_prompt

_MODEL = "qwen2.5-coder:7b"

def _requires_ollama():
    from common.ollama_utils import check_ollama_available
    if not check_ollama_available(_MODEL):
        pytest.skip(f"Ollama model {_MODEL} not available")

def test_real_call_ollama_returns_text():
    _requires_ollama()
    result = call_ollama("Reply with the single word: pong", model=_MODEL, timeout=60)
    assert result is not None
    assert len(result) > 0

def test_real_run_prompt_formats_and_returns(tmp_path):
    _requires_ollama()
    prompt_file = tmp_path / "trivial.prompt"
    prompt_file.write_text("Reply with exactly one word: {word}", encoding="utf-8")
    with patch("common.ollama_utils._PROMPTS_DIR", tmp_path):
        result = run_prompt("trivial", model=_MODEL, timeout=60, word="ping")
    assert result is not None
    assert len(result.strip()) > 0

def test_real_run_prompt_missing_file_returns_none(capsys):
    _requires_ollama()
    result = run_prompt("definitely_does_not_exist_prompt", model=_MODEL, timeout=10)
    assert result is None
    assert "not found" in capsys.readouterr().err

def test_real_analyze_file_with_ollama_returns_list(tmp_path):
    _requires_ollama()
    src = tmp_path / "sample.py"
    src.write_text(
        "def add(a, b):\n    if a is None:\n        raise ValueError('a is None')\n    return a + b\n",
        encoding="utf-8",
    )
    from common.ollama_utils import _PROMPTS_DIR
    result = analyze_file_with_ollama(src, "python", _MODEL, "analyze_library_branches", max_chars=500)
    assert isinstance(result, list)

def test_real_infer_test_type_via_ollama():
    _requires_ollama()
    from parse_test_files import infer_test_type
    body = "result = add(1, 2)\nassert result == 3"
    result = infer_test_type("test_add_returns_sum", body)
    assert result in ("unit", "int_mock", "int_real", "e2e")

def test_prompts_dir_exists_on_disk():
    from common import ollama_utils
    assert ollama_utils._PROMPTS_DIR.exists(), f"prompts dir not found: {ollama_utils._PROMPTS_DIR}"
