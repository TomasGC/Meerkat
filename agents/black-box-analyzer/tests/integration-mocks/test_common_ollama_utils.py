#!/usr/bin/env python3
"""Tests for common/ollama_utils.py — int_mock tests (subprocess patched)"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.ollama_utils import (
    analyze_file_with_ollama,
    call_ollama,
    run_prompt,
)

def test_call_ollama_returns_stdout_on_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '  [{"method": "Foo"}]  '
    with patch("subprocess.run", return_value=mock_result):
        result = call_ollama("prompt", model="qwen2.5-coder:7b", timeout=30)
    assert result == '[{"method": "Foo"}]'

def test_call_ollama_returns_none_on_nonzero_rc(capsys):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "model not found"
    with patch("subprocess.run", return_value=mock_result):
        result = call_ollama("prompt")
    assert result is None
    assert "WARN" in capsys.readouterr().err

def test_call_ollama_returns_none_on_file_not_found(capsys):
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = call_ollama("prompt")
    assert result is None
    assert "ollama" in capsys.readouterr().err.lower()

def test_call_ollama_returns_none_on_timeout(capsys):
    import subprocess as _sp
    with patch("subprocess.run", side_effect=_sp.TimeoutExpired(cmd="ollama", timeout=5)):
        result = call_ollama("prompt", timeout=5)
    assert result is None
    assert "timed out" in capsys.readouterr().err.lower()

def test_call_ollama_passes_model_and_timeout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ok"
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        call_ollama("my prompt", model="llama3:8b", timeout=45)
    call_args = mock_run.call_args
    assert "llama3:8b" in call_args[0][0]
    assert call_args[1]["timeout"] == 45
    assert call_args[1]["input"] == "my prompt"

def test_analyze_file_returns_empty_on_run_prompt_none(tmp_path):
    src = tmp_path / "foo.py"
    src.write_text("def foo(): pass", encoding="utf-8")

    with patch("common.ollama_utils.run_prompt", return_value=None):
        result = analyze_file_with_ollama(src, "python", "model", "prompt_name")

    assert result == []

def test_analyze_file_returns_empty_on_invalid_json(tmp_path, capsys):
    src = tmp_path / "foo.py"
    src.write_text("def foo(): pass", encoding="utf-8")

    with patch("common.ollama_utils.run_prompt", return_value="not json at all"):
        result = analyze_file_with_ollama(src, "python", "model", "prompt_name")

    assert result == []
    assert "WARN" in capsys.readouterr().err

def test_analyze_file_annotates_results(tmp_path):
    src = tmp_path / "bar.cs"
    src.write_text("public void Bar() {}", encoding="utf-8")
    response = json.dumps([{"method": "Bar", "branches": []}])

    with patch("common.ollama_utils.run_prompt", return_value=response):
        result = analyze_file_with_ollama(src, "csharp", "model", "prompt_name")

    assert len(result) == 1
    assert result[0]["source_file"] == str(src)
    assert result[0]["source_file_name"] == "bar.cs"
    assert result[0]["method"] == "Bar"

def test_analyze_file_truncates_large_source(tmp_path):
    src = tmp_path / "big.py"
    src.write_text("x" * 20000, encoding="utf-8")
    captured = {}

    def fake_run_prompt(name, **kwargs):
        captured["source"] = kwargs.get("source", "")
        return "[]"

    with patch("common.ollama_utils.run_prompt", side_effect=fake_run_prompt):
        analyze_file_with_ollama(src, "python", "model", "prompt_name", max_chars=8000)

    assert len(captured["source"]) <= 8000 + len("\n// ... (truncated)")
    assert captured["source"].endswith("(truncated)")

def test_analyze_file_passes_language_and_model(tmp_path):
    src = tmp_path / "svc.go"
    src.write_text("func Foo() {}", encoding="utf-8")
    captured = {}

    def fake_run_prompt(name, model, **kwargs):
        captured["name"] = name
        captured["model"] = model
        captured["language"] = kwargs.get("language")
        return "[]"

    with patch("common.ollama_utils.run_prompt", side_effect=fake_run_prompt):
        analyze_file_with_ollama(src, "go", "qwen2.5-coder:14b", "analyze_library_branches")

    assert captured["name"] == "analyze_library_branches"
    assert captured["model"] == "qwen2.5-coder:14b"
    assert captured["language"] == "go"
