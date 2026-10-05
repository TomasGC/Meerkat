"""lib.ai.model_utils caches only through a cache the caller passes (#21).

It used to import `common.cache` from whichever agent was first on sys.path, so
the cache an agent got depended on import order, and renaming `common` would
have switched it off without a sound.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import lib.ai.model_utils as mu
import pytest


@pytest.fixture
def setup(tmp_path: Path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "p.prompt").write_text("{language}\n{source}", encoding="utf-8")
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    return prompts, f


async def _answer(prompt, role="analyzer", timeout=None):
    return '[{"line": 1}]'


def test_no_cache_argument_means_no_cache(setup):
    prompts, f = setup
    with patch.object(mu, "call_model_async", _answer):
        first = mu.analyze_files_parallel([f], "python", prompt_name="p", prompts_dir=prompts)
        second = mu.analyze_files_parallel([f], "python", prompt_name="p", prompts_dir=prompts)
    assert first == second == [{"line": 1, "source_file": str(f), "source_file_name": "a.py"}]


def test_given_cache_is_read_then_filled(setup):
    prompts, f = setup
    cache = MagicMock()
    cache.get.return_value = None
    with patch.object(mu, "call_model_async", _answer):
        mu.analyze_files_parallel([f], "python", prompt_name="p", prompts_dir=prompts, cache=cache)
    cache.get.assert_called_once_with(f, "p", max_age_days=7)
    cache.set.assert_called_once()


def test_cache_hit_skips_the_model(setup):
    prompts, f = setup
    cache = MagicMock()
    cache.get.return_value = [{"line": 9}]
    model = MagicMock()
    with patch.object(mu, "call_model_async", model):
        result = mu.analyze_files_parallel([f], "python", prompt_name="p", prompts_dir=prompts, cache=cache)
    model.assert_not_called()
    assert result == [{"line": 9}]


def test_no_cache_flag_bypasses_a_given_cache(setup):
    prompts, f = setup
    cache = MagicMock()
    with patch.object(mu, "call_model_async", _answer):
        mu.analyze_files_parallel([f], "python", prompt_name="p", prompts_dir=prompts, cache=cache, no_cache=True)
    cache.get.assert_not_called()
    cache.set.assert_not_called()


def test_module_holds_no_cache_state():
    assert not hasattr(mu, "_CACHE_AVAILABLE")
    assert not hasattr(mu, "_get_cached")
