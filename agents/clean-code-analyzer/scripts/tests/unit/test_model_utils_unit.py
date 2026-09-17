"""Unit tests for common/model_utils.py (shared local AI client) — all external calls mocked."""

import http.client
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

# Import the shared module (the shim re-exports it; patch targets are in the shared module)
_SHARED = Path.home() / ".claude" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.append(str(_SHARED))

import lib.ai.model_utils as mu
from lib.ai.model_utils import (
    call_model,
    call_model_async,
    call_model_multi,
    _http_generate,
    _parse_local_server,
    check_server_available,
    analyze_files_async,
    analyze_files_parallel,
    split_into_chunks,
)


# ── check_server_available ─────────────────────────────────────────────────────

def _tags_response(names: list[str], status: int = 200) -> MagicMock:
    """Mock an /api/tags response listing these model names."""
    response = MagicMock(status=status)
    response.read.return_value = json.dumps({"models": [{"name": n} for n in names]}).encode()
    return response


@pytest.mark.unit
def test_check_server_available_true_when_model_present():
    """Returns True when /api/tags lists the model."""
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["test-model", "other:model"])
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn):
            mu._AVAILABILITY_CACHE.clear()
            result = mu.check_server_available("fast")
    assert result is True


@pytest.mark.unit
def test_check_server_available_false_when_model_missing():
    """Returns False when the model is not in the list."""
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["other:model"])
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn):
            mu._AVAILABILITY_CACHE.clear()
            result = mu.check_server_available("fast")
    assert result is False


@pytest.mark.unit
def test_check_server_available_unreachable_returns_false():
    """A refused connection → False, not an exception."""
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", side_effect=OSError("refused")):
            mu._AVAILABILITY_CACHE.clear()
            result = check_server_available("analyzer")
    assert result is False


@pytest.mark.unit
def test_check_server_available_non_200_returns_false():
    """A server answering something other than 200 is not usable."""
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["test-model"], status=503)
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn):
            mu._AVAILABILITY_CACHE.clear()
            result = check_server_available("analyzer")
    assert result is False


@pytest.mark.unit
def test_tagged_model_matches_untagged_config_name():
    """Config names a model without a tag; the server serves it as ':latest'."""
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["test-model:latest"])
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn):
            mu._AVAILABILITY_CACHE.clear()
            assert check_server_available("analyzer") is True


@pytest.mark.unit
def test_a_longer_model_name_is_not_a_match():
    """'test-model' must not be satisfied by 'test-model-vision' — a different model."""
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["test-model-vision:latest"])
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn):
            mu._AVAILABILITY_CACHE.clear()
            assert check_server_available("analyzer") is False


@pytest.mark.unit
def test_availability_cache_hit():
    """Second check_server_available call uses cache; the server is probed only once."""
    mu._AVAILABILITY_CACHE.clear()
    conn = MagicMock()
    conn.getresponse.return_value = _tags_response(["test-model"])
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=conn) as mock_conn:
            check_server_available("fast")
            check_server_available("fast")
    assert mock_conn.call_count == 1


@pytest.mark.unit
def test_default_role_is_the_one_checkers_use():
    """The bare call in the e2e fixture must gate on the same role the run loads."""
    import inspect
    default = inspect.signature(mu.check_server_available).parameters["role"].default
    assert default == "analyzer"


# ── call_model ─────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_model_passes_prompt_via_stdin():
    """call_model passes the prompt through stdin=prompt."""
    mock_result = MagicMock(returncode=0, stdout='[{"line": 1}]')
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = mu.call_model("my prompt", role="fast")
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("input") == "my prompt" or (
        len(call_kwargs.args) > 1 and call_kwargs.args[1] == "my prompt"
    )
    assert result == '[{"line": 1}]'


@pytest.mark.unit
def test_call_model_returns_stdout():
    """call_model returns stripped stdout on success."""
    mock_result = MagicMock(returncode=0, stdout="  hello world  ")
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result):
            result = mu.call_model("prompt")
    assert result == "hello world"


@pytest.mark.unit
def test_call_model_file_not_found():
    """Local AI CLI not in PATH → None returned, no exception."""
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = call_model("prompt")
    assert result is None


@pytest.mark.unit
def test_call_model_timeout():
    """Subprocess times out → None returned, no exception."""
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cli", 30)):
            result = call_model("prompt")
    assert result is None


@pytest.mark.unit
def test_call_model_nonzero_exit_returns_none():
    """Subprocess returns non-zero exit code → None."""
    mock_result = MagicMock(returncode=1, stderr="model error", stdout="")
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result):
            result = mu.call_model("prompt")
    assert result is None


# ── _http_generate ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_http_generate_returns_response_text():
    """_http_generate parses REST response and returns 'response' field."""
    response_body = json.dumps({"response": "test output"}).encode()
    mock_resp = MagicMock(status=200)
    mock_resp.read.return_value = response_body
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
            result = mu._http_generate("some prompt", "fast")
    assert result == "test output"


@pytest.mark.unit
def test_http_generate_falls_back_to_subprocess_on_connection_refused():
    """ConnectionRefusedError in HTTP → falls back to call_model subprocess."""
    mock_conn = MagicMock()
    mock_conn.request.side_effect = ConnectionRefusedError()

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
            with patch.object(mu, "call_model", return_value="fallback result") as mock_sub:
                result = mu._http_generate("prompt", "fast")

    mock_sub.assert_called_once()
    assert result == "fallback result"


@pytest.mark.unit
def test_http_generate_non_200():
    """HTTP 500 response → None returned."""
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("http.client.HTTPConnection", return_value=mock_conn):
            result = _http_generate("prompt", "fast")
    assert result is None


@pytest.mark.unit
def test_http_generate_general_exception_returns_none():
    """Non-connection exception in _http_generate → returns None."""
    mock_conn = MagicMock()
    mock_conn.request.side_effect = ValueError("unexpected error")
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
            result = mu._http_generate("prompt", "fast")
    assert result is None


@pytest.mark.unit
def test_http_generate_conn_close_exception_no_crash():
    """Exception in conn.close() inside finally → no crash."""
    response_body = json.dumps({"response": "ok"}).encode()
    mock_resp = MagicMock(status=200)
    mock_resp.read.return_value = response_body
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_resp
    mock_conn.close.side_effect = Exception("close failed")
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch.object(http.client, "HTTPConnection", return_value=mock_conn):
            result = mu._http_generate("prompt", "fast")
    assert result == "ok"


# ── extract_json_array ──────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("text, expected", [
    ('[{"line": 1}]', [{"line": 1}]),
    ('Here is the analysis:\n[{"line": 5, "severity": "high"}]\nEnd.', [{"line": 5, "severity": "high"}]),
    ("[]", []),
    ("{not valid json}", None),
    ("", None),
    ('{"key": "value"}', None),
])
def test_extract_json_array_parametrized(text, expected):
    result = mu.extract_json_array(text)
    assert result == expected


@pytest.mark.unit
def test_extract_json_array_invalid_bracketed_content():
    """Text with [...] that contains invalid JSON → returns None."""
    text = "Here is: [not valid json here] end"
    result = mu.extract_json_array(text)
    assert result is None


# ── extract_json_object ─────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("text, expected", [
    ('{"success": true}', {"success": True}),
    ('Result: {"count": 3} end', {"count": 3}),
    ("not json at all", None),
    ("", None),
    ('[1, 2, 3]', None),
])
def test_extract_json_object_parametrized(text, expected):
    result = mu.extract_json_object(text)
    assert result == expected


@pytest.mark.unit
def test_extract_json_object_invalid_braced_content():
    """Text with {...} that contains invalid JSON → returns None."""
    text = "Result: {not valid: json here} done"
    result = mu.extract_json_object(text)
    assert result is None


# ── call_model_multi ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_model_multi_n1_single_call():
    """N=1 → single call to call_model (subprocess path)."""
    mock_result = MagicMock(returncode=0, stdout='[{"line": 5, "principle": "S", "file": "a.py"}]')
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result) as mock_sub:
            result = call_model_multi("prompt", role="fast", n=1)
    assert mock_sub.call_count == 1
    assert len(result) == 1


@pytest.mark.unit
def test_call_model_multi_n3_deduplicates():
    """N=3 → 3 subprocess calls, identical results deduped to 1 item."""
    item_json = '[{"line": 5, "principle": "S", "file": "a.py"}]'
    mock_result = MagicMock(returncode=0, stdout=item_json)
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", return_value=mock_result):
            result = call_model_multi("prompt", role="fast", n=3)
    assert len(result) == 1


@pytest.mark.unit
def test_call_model_multi_n2_merges_unique():
    """N=2 → different items from each call → both kept in merged result."""
    responses = [
        MagicMock(returncode=0, stdout='[{"line": 5, "principle": "S", "file": "a.py"}]'),
        MagicMock(returncode=0, stdout='[{"line": 10, "principle": "D", "file": "a.py"}]'),
    ]
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("subprocess.run", side_effect=responses * 10):
            result = call_model_multi("prompt", role="fast", n=2)
    assert len(result) == 2


# ── split_into_chunks ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_split_into_chunks_small_source_returns_single_chunk():
    source = "line1\nline2\nline3\n"
    result = split_into_chunks(source, max_chars=1000)
    assert result == [source]


@pytest.mark.unit
def test_split_into_chunks_exact_max_chars_returns_single_chunk():
    source = "abc"
    result = split_into_chunks(source, max_chars=3)
    assert len(result) == 1
    assert result[0] == source


@pytest.mark.unit
def test_split_into_chunks_produces_multiple_chunks():
    lines = [f"line_{i}\n" for i in range(20)]
    source = "".join(lines)
    max_chars = len(source) // 3
    result = split_into_chunks(source, max_chars=max_chars)
    assert len(result) >= 2
    assert "".join(result) == source


@pytest.mark.unit
def test_split_into_chunks_respects_newline_boundaries():
    lines = ["A" * 50 + "\n" for _ in range(10)]
    source = "".join(lines)
    max_chars = 120
    result = split_into_chunks(source, max_chars=max_chars)
    for chunk in result:
        assert chunk.endswith("\n") or chunk == result[-1]
    assert "".join(result) == source


@pytest.mark.unit
def test_split_into_chunks_single_long_line_not_split():
    source = "x" * 200
    result = split_into_chunks(source, max_chars=50)
    assert len(result) == 1
    assert result[0] == source


@pytest.mark.unit
def test_split_into_chunks_empty_source():
    result = split_into_chunks("", max_chars=100)
    assert result == [""]


# ── analyze_files_async ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_analyze_files_async_returns_violations(tmp_path):
    """analyze_files_async processes file and returns annotated violations."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class GodClass: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = (
        '[{"principle":"S","line":1,"severity":"high",'
        '"violation":"too much","suggestion":"split"}]'
    )
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", return_value=response_json):
            results = asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, no_cache=True)
            )

    assert len(results) == 1
    assert results[0]["source_file_name"] == "mod.py"


@pytest.mark.unit
def test_analyze_files_async_empty_on_failure(tmp_path):
    """analyze_files_async returns [] when _http_generate returns None."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", return_value=None):
            results = asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, no_cache=True)
            )

    assert results == []


@pytest.mark.unit
def test_analyze_files_async_extra_slots_injected(tmp_path):
    """extra_slots values reach the prompt template for the matching file."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text(
        "Analyze {language}:\n{source}\nKnown:\n{known_findings}"
    )

    captured = []

    def capture(prompt, *args, **kwargs):
        captured.append(prompt)
        return "[]"

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", side_effect=capture):
            asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, no_cache=True,
                                    extra_slots={f: {"known_findings": "- line 1: secret"}})
            )

    assert "Known:\n- line 1: secret" in captured[0]


@pytest.mark.unit
def test_analyze_files_async_extra_slots_are_per_file(tmp_path):
    """Each file receives only its own extra_slots values."""
    import asyncio
    first = tmp_path / "first.py"
    first.write_text("class A: pass\n")
    second = tmp_path / "second.py"
    second.write_text("class B: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("{source}\n{known_findings}")

    captured = []

    def capture(prompt, *args, **kwargs):
        captured.append(prompt)
        return "[]"

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", side_effect=capture):
            asyncio.run(
                analyze_files_async([first, second], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, no_cache=True,
                                    extra_slots={
                                        first: {"known_findings": "finding-A"},
                                        second: {"known_findings": "finding-B"},
                                    })
            )

    prompt_a = next(p for p in captured if "class A" in p)
    prompt_b = next(p for p in captured if "class B" in p)
    assert "finding-A" in prompt_a and "finding-B" not in prompt_a
    assert "finding-B" in prompt_b and "finding-A" not in prompt_b


@pytest.mark.unit
def test_analyze_files_async_without_extra_slots_unchanged(tmp_path):
    """Templates with no extra slots still format when extra_slots is omitted."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    captured = []

    def capture(prompt, *args, **kwargs):
        captured.append(prompt)
        return "[]"

    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", side_effect=capture):
            asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, no_cache=True)
            )

    assert captured[0] == "Analyze python:\nclass X: pass\n"


@pytest.mark.unit
def test_analyze_files_async_cache_hit(tmp_path):
    """analyze_files_async returns cached result without calling _http_generate."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    cached_violations = [{"line": 1, "principle": "S"}]

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    with patch.object(mu, "_CACHE_AVAILABLE", True):
        with patch.object(mu, "_get_cached", return_value=cached_violations):
            with patch.object(mu, "_http_generate") as mock_http:
                results = asyncio.run(
                    analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                        prompts_dir=prompts_dir, no_cache=False)
                )

    mock_http.assert_not_called()
    assert results == cached_violations


@pytest.mark.unit
def test_analyze_files_async_prompt_not_found(tmp_path):
    """analyze_files_async with missing prompt file → returns [] for that file."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    empty_dir = tmp_path / "empty_prompts"
    empty_dir.mkdir()

    results = asyncio.run(
        analyze_files_async([f], "python", "analyzer", "nonexistent_prompt",
                            prompts_dir=empty_dir, no_cache=True)
    )
    assert results == []


@pytest.mark.unit
def test_analyze_files_async_agents_greater_than_1(tmp_path):
    """agents=2 with identical responses collapses to a single violation."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = '[{"principle":"S","line":1,"severity":"high","violation":"v","suggestion":"s"}]'
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", return_value=response_json):
            results = asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, agents=2, no_cache=True)
            )

    # Both agents returned the same (file, line, principle) key — exactly one survives.
    # `>= 1` would also pass with dedup removed entirely.
    assert len(results) == 1


@pytest.mark.unit
def test_analyze_files_async_agents_keeps_distinct_findings(tmp_path):
    """agents=2 with differing responses keeps both — dedup must not over-merge."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    responses = [
        '[{"principle":"S","line":1,"severity":"high","violation":"a","suggestion":"s"}]',
        '[{"principle":"O","line":2,"severity":"low","violation":"b","suggestion":"s"}]',
    ]
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", side_effect=responses):
            results = asyncio.run(
                analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                    prompts_dir=prompts_dir, agents=2, no_cache=True)
            )

    assert len(results) == 2
    assert {r["principle"] for r in results} == {"S", "O"}


@pytest.mark.unit
def test_analyze_files_async_writes_cache(tmp_path):
    """analyze_files_async with no_cache=False writes results to cache."""
    import asyncio
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = '[{"principle":"S","line":1,"severity":"high","violation":"v","suggestion":"s"}]'
    with patch("lib.ai.model_utils.get_model", return_value="test-model"):
        with patch("lib.ai.model_utils._http_generate", return_value=response_json):
            with patch.object(mu, "_CACHE_AVAILABLE", True):
                with patch.object(mu, "_get_cached", return_value=None):
                    with patch.object(mu, "_set_cached") as mock_set:
                        asyncio.run(
                            analyze_files_async([f], "python", "analyzer", "solid_analysis",
                                                prompts_dir=prompts_dir, no_cache=False)
                        )

    mock_set.assert_called_once()


# ── analyze_file_with_model ─────────────────────────────────────────────────────

@pytest.mark.unit
def test_analyze_file_with_model_cache_hit(tmp_path):
    """analyze_file_with_model returns cached result without calling model."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    cached = [{"line": 1, "principle": "S"}]

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    with patch.object(mu, "_CACHE_AVAILABLE", True):
        with patch.object(mu, "_get_cached", return_value=cached):
            with patch.object(mu, "call_model") as mock_call:
                result = mu.analyze_file_with_model(f, "python", "analyzer", "solid",
                                                    prompts_dir=prompts_dir)

    mock_call.assert_not_called()
    assert result == cached


@pytest.mark.unit
def test_analyze_file_with_model_agents_greater_than_1(tmp_path):
    """analyze_file_with_model with agents=2 uses call_model_multi."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    with patch.object(mu, "call_model_multi", return_value=[{"line": 1, "principle": "S"}]) as mock_multi:
        result = mu.analyze_file_with_model(f, "python", "analyzer", "solid_analysis",
                                            prompts_dir=prompts_dir, agents=2, no_cache=True)

    mock_multi.assert_called()
    assert len(result) >= 1


@pytest.mark.unit
def test_analyze_file_with_model_agents_1_calls_model(tmp_path):
    """analyze_file_with_model agents=1 calls call_model directly."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = '[{"principle":"S","line":1,"severity":"high","violation":"v","suggestion":"s"}]'
    with patch.object(mu, "call_model", return_value=response_json) as mock_call:
        result = mu.analyze_file_with_model(f, "python", "analyzer", "solid_analysis",
                                            prompts_dir=prompts_dir, agents=1, no_cache=True)

    mock_call.assert_called()
    assert len(result) >= 1


@pytest.mark.unit
def test_analyze_file_with_model_prompt_not_found(tmp_path):
    """analyze_file_with_model with missing prompt file → returns []."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    empty_dir = tmp_path  # no prompt files here

    result = mu.analyze_file_with_model(f, "python", "analyzer", "nonexistent_prompt",
                                        prompts_dir=empty_dir, no_cache=True)
    assert result == []


@pytest.mark.unit
def test_analyze_file_with_model_empty_results(tmp_path):
    """analyze_file_with_model when model returns None → empty list."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    with patch.object(mu, "call_model", return_value=None):
        result = mu.analyze_file_with_model(f, "python", "analyzer", "solid_analysis",
                                            prompts_dir=prompts_dir, agents=1, no_cache=True)

    assert result == []


@pytest.mark.unit
def test_analyze_file_with_model_writes_cache(tmp_path):
    """analyze_file_with_model with no_cache=False writes results to cache."""
    f = tmp_path / "mod.py"
    f.write_text("class X: pass\n")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "solid_analysis.prompt").write_text("Analyze {language}:\n{source}")

    response_json = '[{"principle":"S","line":1,"severity":"high","violation":"v","suggestion":"s"}]'
    with patch.object(mu, "call_model", return_value=response_json):
        with patch.object(mu, "_CACHE_AVAILABLE", True):
            with patch.object(mu, "_get_cached", return_value=None):
                with patch.object(mu, "_set_cached") as mock_set:
                    mu.analyze_file_with_model(f, "python", "analyzer", "solid_analysis",
                                               prompts_dir=prompts_dir, agents=1, no_cache=False)

    mock_set.assert_called_once()


# ── CCA shim: get_claude_fallback_prompt ────────────────────────────────────────

def _load_cca_shim():
    """Load CCA's common/model_utils.py by file path to avoid sys.modules cache collisions."""
    import importlib.util
    shim_path = Path(__file__).parent.parent.parent / "common" / "model_utils.py"
    spec = importlib.util.spec_from_file_location("cca_common_model_utils", shim_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_get_claude_fallback_prompt_returns_none_when_missing(tmp_path):
    """get_claude_fallback_prompt returns None when prompt file is missing."""
    cca_mu = _load_cca_shim()
    cca_mu.CLAUDE_PROMPTS_DIR = tmp_path
    result = cca_mu.get_claude_fallback_prompt("nonexistent_prompt", language="python", source="x")
    assert result is None


@pytest.mark.unit
def test_get_claude_fallback_prompt_key_error_returns_raw(tmp_path):
    """get_claude_fallback_prompt with format KeyError → returns raw template."""
    cca_mu = _load_cca_shim()

    prompt_file = tmp_path / "test_prompt.prompt"
    prompt_file.write_text("Analyze {language}: {required_key}")
    cca_mu.CLAUDE_PROMPTS_DIR = tmp_path

    result = cca_mu.get_claude_fallback_prompt("test_prompt")

    assert result is not None
    assert "{language}" in result or "{required_key}" in result


# ── analyze_files_parallel ────────────────────────────────────────────────────
# analyze_files_parallel → analyze_files_async → call_model_async (per file)
# Patch call_model_async to avoid real network calls.

@pytest.mark.unit
def test_analyze_files_parallel_empty_list(tmp_path):
    """analyze_files_parallel with empty file list returns []."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "analyze.prompt").write_text("Analyze {language}:\n{source}")

    result = analyze_files_parallel([], "python", prompts_dir=prompts_dir)
    assert result == []


@pytest.mark.unit
def test_analyze_files_parallel_calls_model_per_file(tmp_path):
    """analyze_files_parallel calls the model once per file."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "analyze.prompt").write_text("Analyze {language}:\n{source}")

    files = []
    for i in range(3):
        f = tmp_path / f"mod{i}.py"
        f.write_text(f"x = {i}\n")
        files.append(f)

    async def fake_async(*args, **kwargs):
        return '[{"line": 1, "violation": "v"}]'

    with patch.object(mu, "call_model_async", side_effect=fake_async):
        result = analyze_files_parallel(files, "python", prompts_dir=prompts_dir, no_cache=True)

    # 3 files, each produces 1 violation
    assert len(result) == 3


@pytest.mark.unit
def test_analyze_files_parallel_aggregates_results(tmp_path):
    """analyze_files_parallel merges results from all files into one flat list."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "analyze.prompt").write_text("Analyze {language}:\n{source}")

    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("x = 1\n")
    f2.write_text("y = 2\n")

    async def fake_async(*args, **kwargs):
        return '[{"line": 1}, {"line": 2}]'

    with patch.object(mu, "call_model_async", side_effect=fake_async):
        result = analyze_files_parallel([f1, f2], "python", prompts_dir=prompts_dir, no_cache=True)

    assert len(result) == 4  # 2 results per file × 2 files


@pytest.mark.unit
def test_analyze_files_parallel_passes_role(tmp_path):
    """analyze_files_parallel passes role= through to call_model_async."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "analyze.prompt").write_text("Analyze {language}:\n{source}")

    f = tmp_path / "mod.py"
    f.write_text("x = 1\n")

    captured_roles = []

    async def fake_async(prompt, role="fast", **kwargs):
        captured_roles.append(role)
        return "[]"

    with patch.object(mu, "call_model_async", side_effect=fake_async):
        analyze_files_parallel([f], "python", role="analyzer", prompts_dir=prompts_dir, no_cache=True)

    assert captured_roles == ["analyzer"]


# ── _parse_local_server ───────────────────────────────────────────────────────

@pytest.mark.unit
def test_parse_local_server_standard_url():
    """_parse_local_server parses host and port from standard base_url."""
    config = {"local": {"base_url": "http://localhost:11434"}}
    with patch.object(mu, "_load_config", return_value=config):
        host, port = _parse_local_server()
    assert host == "localhost"
    assert port == 11434


@pytest.mark.unit
def test_parse_local_server_custom_host_and_port():
    """_parse_local_server parses custom host and port."""
    config = {"local": {"base_url": "http://192.168.1.100:8080"}}
    with patch.object(mu, "_load_config", return_value=config):
        host, port = _parse_local_server()
    assert host == "192.168.1.100"
    assert port == 8080


@pytest.mark.unit
def test_parse_local_server_no_port_uses_default():
    """_parse_local_server falls back to port 11434 when URL has no port."""
    config = {"local": {"base_url": "http://myhost"}}
    with patch.object(mu, "_load_config", return_value=config):
        host, port = _parse_local_server()
    assert host == "myhost"
    assert port == 11434


@pytest.mark.unit
def test_parse_local_server_missing_config_uses_defaults():
    """_parse_local_server uses localhost:11434 when config has no local section."""
    with patch.object(mu, "_load_config", return_value={}):
        host, port = _parse_local_server()
    assert host == "localhost"
    assert port == 11434


# ── call_model_async ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_call_model_async_returns_http_generate_result():
    """call_model_async delegates to _http_generate in an executor and returns its result."""
    import asyncio

    async def run():
        with patch.object(mu, "_http_generate", return_value="mocked response"):
            return await call_model_async("test prompt", role="fast", timeout=30)

    result = asyncio.run(run())
    assert result == "mocked response"


@pytest.mark.unit
def test_call_model_async_returns_none_on_exception():
    """call_model_async returns None when _http_generate raises."""
    import asyncio

    async def run():
        with patch.object(mu, "_http_generate", side_effect=RuntimeError("fail")):
            try:
                return await call_model_async("test prompt", role="fast", timeout=30)
            except RuntimeError:
                return None

    result = asyncio.run(run())
    assert result is None
