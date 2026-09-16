#!/usr/bin/env python3
"""Tests for common/model_utils.py — int_mock tests (subprocess patched)"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.model_utils import (
    analyze_file_with_model,
    call_model,
    run_prompt,
    PROMPTS_DIR,
)


def test_call_model_returns_stdout_on_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '  [{"method": "Foo"}]  '
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result):
            result = call_model("prompt", role="fast", timeout=30)
    assert result == '[{"method": "Foo"}]'


def test_call_model_returns_none_on_nonzero_rc(capsys):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "model not found"
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result):
            result = call_model("prompt")
    assert result is None
    assert "WARN" in capsys.readouterr().err


def test_call_model_returns_none_on_file_not_found(capsys):
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = call_model("prompt")
    assert result is None


def test_call_model_returns_none_on_timeout(capsys):
    import subprocess as _sp
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", side_effect=_sp.TimeoutExpired(cmd="cli", timeout=5)):
            result = call_model("prompt", timeout=5)
    assert result is None
    assert "timed out" in capsys.readouterr().err.lower()


def test_call_model_passes_role_and_timeout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ok"
    with patch("lib.ai.model_utils.get_model", return_value="test-model") as mock_get:
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            call_model("my prompt", role="deep", timeout=45)
    mock_get.assert_called_with("deep")
    call_args = mock_run.call_args
    assert call_args[1]["timeout"] == 45
    assert call_args[1]["input"] == "my prompt"


def test_analyze_file_returns_empty_on_call_model_none(tmp_path):
    src = tmp_path / "foo.py"
    src.write_text("def foo(): pass", encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "prompt_name.prompt").write_text("{language}:{source}")

    with patch("lib.ai.model_utils.call_model", return_value=None):
        result = analyze_file_with_model(src, "python", "analyzer", "prompt_name",
                                         prompts_dir=prompts_dir)
    assert result == []


def test_analyze_file_annotates_results(tmp_path):
    src = tmp_path / "bar.cs"
    src.write_text("public void Bar() {}", encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "prompt_name.prompt").write_text("{language}:{source}")

    response = json.dumps([{"method": "Bar", "branches": []}])
    with patch("lib.ai.model_utils.call_model", return_value=response):
        result = analyze_file_with_model(src, "csharp", "analyzer", "prompt_name",
                                         prompts_dir=prompts_dir, no_cache=True)

    assert len(result) == 1
    assert result[0]["source_file"] == str(src)
    assert result[0]["source_file_name"] == "bar.cs"
    assert result[0]["method"] == "Bar"


def test_analyze_file_passes_language_and_role(tmp_path):
    src = tmp_path / "svc.go"
    src.write_text("func Foo() {}", encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "analyze_library_branches.prompt").write_text("{language}:{source}")

    captured = {}

    def fake_call_model(prompt, role="fast", timeout=120):
        captured["role"] = role
        captured["language"] = "go" if "go" in prompt else None
        return "[]"

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils.call_model", side_effect=fake_call_model):
            analyze_file_with_model(src, "go", "deep", "analyze_library_branches",
                                    prompts_dir=prompts_dir)

    assert captured["role"] == "deep"
