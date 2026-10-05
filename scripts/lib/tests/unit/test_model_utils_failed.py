"""Unit tests for the `failed` out-parameter of lib.ai.model_utils.analyze_files_parallel.

`failed` lets a caller tell "the AI found nothing" (`[]`) apart from "the AI call
produced no usable answer" (None, unparseable, exception), so a cache never stores
a failure as a clean result. call_model_async is replaced per test; no server needed.
"""

from pathlib import Path
from unittest.mock import patch

import lib.ai.model_utils as mu
import pytest

_ITEM = '[{"line": 3, "description": "d"}]'


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "p.prompt").write_text("{language}\n{source}", encoding="utf-8")
    return d


def _file(tmp_path: Path, name: str) -> Path:
    f = tmp_path / name
    f.write_text("x = 1\n", encoding="utf-8")
    return f


def _responses(by_file: dict[str, list]):
    """call_model_async stand-in: pops the next response queued for the file named in the prompt."""

    async def fake(prompt, role="analyzer", timeout=None):
        for name, queue in by_file.items():
            if name in prompt:
                resp = queue.pop(0)
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"no response queued for prompt {prompt!r}")

    return fake


def _run(files, prompts_dir, by_file, failed, agents=1):
    with patch.object(mu, "call_model_async", side_effect=_responses(by_file)):
        return mu.analyze_files_parallel(
            files, "python", prompt_name="p", prompts_dir=prompts_dir, agents=agents, no_cache=True, failed=failed
        )


def _named(tmp_path: Path, name: str) -> Path:
    """A file whose content contains its own name, so the fake can route by prompt text."""
    f = tmp_path / name
    f.write_text(f"# {name}\nx = 1\n", encoding="utf-8")
    return f


def test_none_response_marks_file_failed(tmp_path, prompts_dir):
    f = _named(tmp_path, "a.py")
    failed: set = set()
    assert _run([f], prompts_dir, {"a.py": [None]}, failed) == []
    assert failed == {f}


def test_unparseable_response_marks_file_failed(tmp_path, prompts_dir):
    f = _named(tmp_path, "a.py")
    failed: set = set()
    assert _run([f], prompts_dir, {"a.py": ["sorry, I cannot help with that"]}, failed) == []
    assert failed == {f}


def test_empty_list_response_is_clean_not_failed(tmp_path, prompts_dir):
    f = _named(tmp_path, "a.py")
    failed: set = set()
    assert _run([f], prompts_dir, {"a.py": ["[]"]}, failed) == []
    assert failed == set()


def test_exception_marks_only_that_file_failed(tmp_path, prompts_dir):
    bad = _named(tmp_path, "bad.py")
    good = _named(tmp_path, "good.py")
    failed: set = set()
    items = _run([bad, good], prompts_dir, {"bad.py": [RuntimeError("boom")], "good.py": [_ITEM]}, failed)
    assert failed == {bad}
    assert [i["source_file"] for i in items] == [str(good)]


def test_agents_one_good_one_failed_response_not_failed(tmp_path, prompts_dir):
    f = _named(tmp_path, "a.py")
    failed: set = set()
    items = _run([f], prompts_dir, {"a.py": [None, _ITEM]}, failed, agents=2)
    assert failed == set()
    assert len(items) == 1


def test_agents_all_responses_failed_marks_file_failed(tmp_path, prompts_dir):
    f = _named(tmp_path, "a.py")
    failed: set = set()
    assert _run([f], prompts_dir, {"a.py": [None, "not json"]}, failed, agents=2) == []
    assert failed == {f}


@pytest.mark.parametrize(
    "responses,expected_sources",
    [
        ({"a.py": [_ITEM], "b.py": [None]}, ["a.py"]),
        ({"a.py": ["[]"], "b.py": ["garbage"]}, []),
        ({"a.py": [_ITEM], "b.py": [RuntimeError("boom")]}, ["a.py"]),
    ],
)
def test_failed_none_returns_same_items_as_with_failed_set(tmp_path, prompts_dir, responses, expected_sources):
    """failed=None (every existing caller) yields the pre-change items, identical to a tracked run."""
    a = _named(tmp_path, "a.py")
    b = _named(tmp_path, "b.py")
    untracked = _run([a, b], prompts_dir, {k: list(v) for k, v in responses.items()}, None)
    tracked = _run([a, b], prompts_dir, {k: list(v) for k, v in responses.items()}, set())
    assert [Path(i["source_file"]).name for i in untracked] == expected_sources
    assert untracked == tracked
