"""Unit tests for common/ollama_utils.py — all external calls mocked."""

import http.client
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common.ollama_utils as ou
from common.ollama_utils import (
    call_ollama,
    call_ollama_multi,
    _http_generate,
    check_ollama_available,
    analyze_files_async,
    split_into_chunks,
)


# ── check_ollama_available ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_check_ollama_available_true_when_model_present():
    """Returns True when subprocess shows model in list."""
    mock_result = MagicMock(returncode=0, stdout="NAME\nqwen2.5-coder:7b\nother:model\n")
    with patch("subprocess.run", return_value=mock_result):
        ou._AVAILABILITY_CACHE.clear()
        result = ou.check_ollama_available("qwen2.5-coder:7b")
    assert result is True


@pytest.mark.unit
def test_check_ollama_available_false_when_model_missing():
    """Returns False when model not in list."""
    mock_result = MagicMock(returncode=0, stdout="NAME\nother:model\n")
    with patch("subprocess.run", return_value=mock_result):
        ou._AVAILABILITY_CACHE.clear()
        result = ou.check_ollama_available("qwen2.5-coder:7b")
    assert result is False


# ── call_ollama ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_ollama_passes_prompt_via_stdin():
    """call_ollama passes the prompt through stdin=prompt."""
    mock_result = MagicMock(returncode=0, stdout='[{"line": 1}]')
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = ou.call_ollama("my prompt", model="qwen2.5-coder:7b")
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("input") == "my prompt" or (
        len(call_kwargs.args) > 1 and call_kwargs.args[1] == "my prompt"
    )
    assert result == '[{"line": 1}]'


@pytest.mark.unit
def test_call_ollama_returns_stdout():
    """call_ollama returns stripped stdout on success."""
    mock_result = MagicMock(returncode=0, stdout="  hello world  ")
    with patch("subprocess.run", return_value=mock_result):
        result = ou.call_ollama("prompt")
    assert result == "hello world"


# ── _http_generate ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_http_generate_returns_response_text():
    """_http_generate parses Ollama REST response and returns 'response' field."""
    response_body = json.dumps({"response": "test output"}).encode()
    mock_resp = MagicMock(status=200)
    mock_resp.read.return_value = response_body
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp

    with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
        result = ou._http_generate("some prompt", "qwen2.5-coder:7b")
    assert result == "test output"


@pytest.mark.unit
def test_http_generate_falls_back_to_subprocess_on_connection_refused():
    """ConnectionRefusedError in HTTP → falls back to call_ollama subprocess."""
    mock_conn = MagicMock()
    mock_conn.request.side_effect = ConnectionRefusedError()

    with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
        with patch.object(ou, "call_ollama", return_value="fallback result") as mock_sub:
            result = ou._http_generate("prompt", "qwen2.5-coder:7b")

    mock_sub.assert_called_once()
    assert result == "fallback result"


# ── extract_json_array ──────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("text, expected", [
    # Direct JSON array
    ('[{"line": 1}]', [{"line": 1}]),
    # Wrapped in prose
    ('Here is the analysis:\n[{"line": 5, "severity": "high"}]\nEnd.', [{"line": 5, "severity": "high"}]),
    # Empty array
    ("[]", []),
    # Invalid JSON
    ("{not valid json}", None),
    # Empty string
    ("", None),
    # JSON object (not array)
    ('{"key": "value"}', None),
])
def test_extract_json_array_parametrized(text, expected):
    result = ou.extract_json_array(text)
    assert result == expected


# ── extract_json_object ─────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("text, expected", [
    # Direct JSON object
    ('{"success": true}', {"success": True}),
    # Wrapped in prose
    ('Result: {"count": 3} end', {"count": 3}),
    # Invalid JSON
    ("not json at all", None),
    # Empty string
    ("", None),
    # JSON array with no objects inside (no braces to extract)
    ('[1, 2, 3]', None),
])
def test_extract_json_object_parametrized(text, expected):
    result = ou.extract_json_object(text)
    assert result == expected


# ── call_ollama error paths ─────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_ollama_file_not_found():
    """ollama not in PATH → None returned, no exception."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = call_ollama("prompt")
    assert result is None


@pytest.mark.unit
def test_call_ollama_timeout():
    """Ollama subprocess times out → None returned, no exception."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ollama", 30)):
        result = call_ollama("prompt")
    assert result is None


# ── _http_generate error paths ──────────────────────────────────────────────────

@pytest.mark.unit
def test_http_generate_non_200():
    """HTTP 500 response → None returned."""
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp
    with patch("http.client.HTTPConnection", return_value=mock_conn):
        result = _http_generate("prompt", "model")
    assert result is None


# ── check_ollama_available caching ──────────────────────────────────────────────

@pytest.mark.unit
def test_availability_cache_hit():
    """Second check_ollama_available call uses cache; subprocess called only once."""
    ou._AVAILABILITY_CACHE.clear()
    mock_result = MagicMock(returncode=0, stdout="qwen2.5-coder:7b\n")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        check_ollama_available("qwen2.5-coder:7b")
        check_ollama_available("qwen2.5-coder:7b")  # second call — should hit cache
    assert mock_sub.call_count == 1


# ── get_claude_fallback_prompt ──────────────────────────────────────────────────

@pytest.mark.unit
def test_get_claude_fallback_prompt_returns_none_when_missing(tmp_path):
    """get_claude_fallback_prompt returns None when prompt file is missing."""
    original = ou.CLAUDE_PROMPTS_DIR
    ou.CLAUDE_PROMPTS_DIR = tmp_path  # empty directory
    try:
        result = ou.get_claude_fallback_prompt("nonexistent_prompt", language="python", source="x")
    finally:
        ou.CLAUDE_PROMPTS_DIR = original
    assert result is None


# ── call_ollama_multi ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_ollama_multi_n1_single_call():
    """N=1 → single call to call_ollama (subprocess path)."""
    mock_result = MagicMock(returncode=0, stdout='[{"line": 5, "principle": "S", "file": "a.py"}]')
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        result = call_ollama_multi("prompt", "qwen2.5-coder:7b", n=1)
    assert mock_sub.call_count == 1
    assert len(result) == 1


@pytest.mark.unit
def test_call_ollama_multi_n3_deduplicates():
    """N=3 → 3 subprocess calls, identical results deduped to 1 item."""
    item_json = '[{"line": 5, "principle": "S", "file": "a.py"}]'
    mock_result = MagicMock(returncode=0, stdout=item_json)
    with patch("subprocess.run", return_value=mock_result):
        result = call_ollama_multi("prompt", "qwen2.5-coder:7b", n=3)
    assert len(result) == 1  # deduplicated by (file, line, principle)


@pytest.mark.unit
def test_call_ollama_multi_n2_merges_unique():
    """N=2 → different items from each call → both kept in merged result."""
    responses = [
        MagicMock(returncode=0, stdout='[{"line": 5, "principle": "S", "file": "a.py"}]'),
        MagicMock(returncode=0, stdout='[{"line": 10, "principle": "D", "file": "a.py"}]'),
    ]
    with patch("subprocess.run", side_effect=responses * 10):
        result = call_ollama_multi("prompt", "qwen2.5-coder:7b", n=2)
    assert len(result) == 2


# ── analyze_files_async ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_analyze_files_async_returns_violations(tmp_path):
    """analyze_files_async processes file and returns annotated violations."""
    f = tmp_path / "mod.py"
    f.write_text("class GodClass: pass\n")

    # Create a fake prompt template
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = (
        '[{"principle":"S","line":1,"severity":"high",'
        '"violation":"too much","suggestion":"split"}]'
    )
    original_dir = ou._PROMPTS_DIR
    ou._PROMPTS_DIR = prompts_dir
    try:
        with patch("common.ollama_utils._http_generate", return_value=response_json):
            import asyncio
            results = asyncio.run(
                analyze_files_async([f], "python", "qwen3:8b", "solid_analysis", no_cache=True)
            )
    finally:
        ou._PROMPTS_DIR = original_dir

    assert len(results) == 1
    assert results[0]["source_file_name"] == "mod.py"


@pytest.mark.unit
def test_analyze_files_async_empty_on_ollama_failure(tmp_path):
    """analyze_files_async returns [] when _http_generate returns None."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    original_dir = ou._PROMPTS_DIR
    ou._PROMPTS_DIR = prompts_dir
    try:
        with patch("common.ollama_utils._http_generate", return_value=None):
            import asyncio
            results = asyncio.run(
                analyze_files_async([f], "python", "qwen3:8b", "solid_analysis", no_cache=True)
            )
    finally:
        ou._PROMPTS_DIR = original_dir

    assert results == []


# ── split_into_chunks ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_split_into_chunks_small_source_returns_single_chunk():
    """Source shorter than max_chars → single-element list containing full source."""
    source = "line1\nline2\nline3\n"
    result = split_into_chunks(source, max_chars=1000)
    assert result == [source]


@pytest.mark.unit
def test_split_into_chunks_exact_max_chars_returns_single_chunk():
    """Source whose length equals max_chars exactly → single chunk (no split)."""
    source = "abc"
    result = split_into_chunks(source, max_chars=3)
    assert len(result) == 1
    assert result[0] == source


@pytest.mark.unit
def test_split_into_chunks_produces_multiple_chunks():
    """Source larger than max_chars → split into 2+ chunks, all content preserved."""
    lines = [f"line_{i}\n" for i in range(20)]
    source = "".join(lines)
    max_chars = len(source) // 3  # force at least 3 chunks
    result = split_into_chunks(source, max_chars=max_chars)
    assert len(result) >= 2
    assert "".join(result) == source  # no data lost


@pytest.mark.unit
def test_split_into_chunks_respects_newline_boundaries():
    """Chunks split on line boundaries — no line is torn across two chunks."""
    lines = ["A" * 50 + "\n" for _ in range(10)]
    source = "".join(lines)
    max_chars = 120  # each line is 51 chars; max fits 2 lines
    result = split_into_chunks(source, max_chars=max_chars)
    for chunk in result:
        # Every chunk either ends with \n or is the final chunk
        assert chunk.endswith("\n") or chunk == result[-1]
    assert "".join(result) == source


@pytest.mark.unit
def test_split_into_chunks_single_long_line_not_split():
    """A single line exceeding max_chars cannot split on newline → returned as single chunk."""
    source = "x" * 200  # no newlines at all
    result = split_into_chunks(source, max_chars=50)
    # Cannot split without newlines — entire source in one oversized chunk
    assert len(result) == 1
    assert result[0] == source


# ── check_ollama_available FileNotFoundError ────────────────────────────────────

@pytest.mark.unit
def test_check_ollama_available_file_not_found_returns_false():
    """FileNotFoundError (ollama binary absent) → False, not an exception."""
    ou._AVAILABILITY_CACHE.clear()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_ollama_available("devstral")
    assert result is False


@pytest.mark.unit
def test_split_into_chunks_empty_source():
    """Empty source → single-element list (len(source) == 0 <= max_chars)."""
    result = split_into_chunks("", max_chars=100)
    assert result == [""]
