#!/usr/bin/env python3
"""Tests for common/model_utils.py — int_real tests (live local AI required)"""

from pathlib import Path
from unittest.mock import patch

import pytest

from common.model_utils import analyze_file_with_model, call_model, run_prompt, PROMPTS_DIR


def _requires_local_ai():
    from common.model_utils import check_server_available
    if not check_server_available("fast"):
        pytest.skip("Local AI model not available")


def test_real_call_model_returns_text():
    _requires_local_ai()
    result = call_model("Reply with the single word: pong", role="fast", timeout=60)
    assert result is not None
    assert len(result) > 0


def test_real_run_prompt_formats_and_returns(tmp_path):
    _requires_local_ai()
    prompt_file = tmp_path / "trivial.prompt"
    prompt_file.write_text("Reply with exactly one word: {word}", encoding="utf-8")
    result = run_prompt("trivial", tmp_path, role="fast", timeout=60, word="ping")
    assert result is not None
    assert len(result.strip()) > 0


def test_real_run_prompt_missing_file_returns_none(capsys):
    _requires_local_ai()
    result = run_prompt("definitely_does_not_exist_prompt", PROMPTS_DIR, role="fast", timeout=10)
    assert result is None
    assert "not found" in capsys.readouterr().err


def test_real_analyze_file_with_model_returns_list(tmp_path):
    _requires_local_ai()
    src = tmp_path / "sample.py"
    src.write_text(
        "def add(a, b):\n    if a is None:\n        raise ValueError('a is None')\n    return a + b\n",
        encoding="utf-8",
    )
    result = analyze_file_with_model(src, "python", "fast", "analyze_library_branches",
                                     prompts_dir=PROMPTS_DIR, max_chars=500)
    assert isinstance(result, list)


def test_real_infer_test_type_via_local_ai():
    _requires_local_ai()
    from parse_test_files import infer_test_type
    body = "result = add(1, 2)\nassert result == 3"
    result = infer_test_type("test_add_returns_sum", body)
    assert result in ("unit", "int_mock", "int_real", "e2e")


def test_prompts_dir_exists_on_disk():
    assert PROMPTS_DIR.exists(), f"prompts dir not found: {PROMPTS_DIR}"
