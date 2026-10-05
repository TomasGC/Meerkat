"""Unit tests for lib.testing.golden — replay identification, failure reporting, diffing."""

import asyncio
import json
from pathlib import Path

import lib.ai.model_utils as model_utils
import pytest
from lib.testing import golden

_TEMPLATE = "Review this {language} code.\nSource:\n{source}\nKnown:\n{known_findings}\nReturn JSON.\n"
_SOURCE = "def f():\n    return 1\n"


@pytest.fixture
def setup(tmp_path):
    project = tmp_path / "demo_project"
    (project / "pkg").mkdir(parents=True)
    (project / "pkg" / "app.py").write_text(_SOURCE, encoding="utf-8")
    responses = tmp_path / "golden" / "ai_responses" / "cca"
    responses.mkdir(parents=True)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "review.prompt").write_text(_TEMPLATE, encoding="utf-8")
    (prompts / "other.prompt").write_text("Something else entirely: {source}", encoding="utf-8")
    return project, responses, prompts


def _record(responses: Path, name: str, entries: dict) -> None:
    (responses / f"{name}.json").write_text(json.dumps(entries), encoding="utf-8")


def _call(prompt: str) -> str:
    return asyncio.run(model_utils.call_model_async(prompt, role="analyzer"))


def _render(source: str = _SOURCE) -> str:
    return _TEMPLATE.format(language="python", source=source, known_findings="- line 1: x")


def test_matching_call_returns_recorded_response(setup):
    project, responses, prompts = setup
    _record(responses, "review", {"pkg/app.py": '[{"line": 2}]'})
    with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1]) as state:
        assert _call(_render()) == '[{"line": 2}]'
    assert state.calls == 1


def test_unmatched_call_raises(setup):
    project, responses, prompts = setup
    _record(responses, "review", {"pkg/app.py": "[]"})
    with pytest.raises(golden.ReplayError, match="matched none templates"):
        with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1], strict_unused=False):
            with pytest.raises(golden.ReplayError):
                _call("a prompt no template produces")


def test_unknown_source_raises(setup):
    project, responses, prompts = setup
    _record(responses, "review", {"pkg/app.py": "[]"})
    with pytest.raises(golden.ReplayError, match="no fixture files"):
        with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1], strict_unused=False):
            with pytest.raises(golden.ReplayError):
                _call(_render(source="print('not a fixture file')\n"))


def test_missing_response_raises_even_if_caller_swallows_it(setup):
    project, responses, prompts = setup
    with pytest.raises(golden.ReplayError, match="no recorded response for prompt 'review', file 'pkg/app.py'"):
        with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1]):
            try:
                _call(_render())
            except golden.ReplayError:
                pass  # analyze_files_async swallows per-file exceptions the same way


def test_unused_response_is_reported(setup):
    project, responses, prompts = setup
    _record(responses, "review", {"pkg/app.py": "[]"})
    with pytest.raises(golden.ReplayError, match=r"never used \(stale fixture\): review: pkg/app.py"):
        with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1]):
            pass


def test_unused_response_tolerated_when_not_strict(setup):
    project, responses, prompts = setup
    _record(responses, "review", {"pkg/app.py": "[]"})
    with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1], strict_unused=False) as state:
        pass
    assert state.unused() == ["review: pkg/app.py"]


def test_server_probe_reports_available_inside_replay_only(setup):
    project, responses, prompts = setup
    real_probe, real_call = model_utils._model_listed, model_utils.call_model_async
    with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1]):
        assert model_utils.check_server_available("analyzer") is True
    assert model_utils._model_listed is real_probe
    assert model_utils.call_model_async is real_call


def test_synchronous_model_call_is_forbidden(setup):
    project, responses, prompts = setup
    with pytest.raises(golden.ReplayError, match="synchronous model call"):
        with golden.replay(project, "cca", prompts, golden_dir=responses.parents[1]):
            with pytest.raises(golden.ReplayError):
                model_utils.call_model("anything")


def test_normalise_makes_posix_relative_paths_and_sorts(tmp_path):
    root = tmp_path / "proj"
    violations = [
        {"file": str(root / "pkg" / "b.py"), "line": 3, "principle": "X", "message": "m"},
        {"file": "pkg\\a.py", "line": 10, "principle": "X", "message": "m"},
        {"file": "pkg\\a.py", "line": 2, "principle": "X", "message": "m"},
    ]
    out = golden.normalise(violations, root)
    assert [(v["file"], v["line"]) for v in out] == [("pkg/a.py", 2), ("pkg/a.py", 10), ("pkg/b.py", 3)]


def test_compare_reports_missing_unexpected_and_changed():
    base = {"file": "a.py", "principle": "P", "severity": "high", "message": "m", "suggestion": "s"}
    expected = [{**base, "line": 1}, {**base, "line": 5}]
    actual = [{**base, "line": 1, "severity": "low"}, {**base, "line": 9}]
    diff = golden.compare(actual, expected)
    assert diff == [
        "missing    a.py:5 [P]: m",
        "unexpected a.py:9 [P]: m",
        "changed    a.py:1 [P] severity: expected 'high', got 'low'",
    ]
    assert golden.compare(expected, expected) == []


def test_metadata_resolves_outside_the_scanned_project():
    """Expected files and recorded responses live under fixtures/golden, never in the project."""
    assert golden.golden_path("python_project") == golden.golden_root() / "python_project"
    assert golden.expected_path("python_project", "cca").is_relative_to(golden.golden_root())
    assert not golden.golden_root().is_relative_to(golden.projects_root())


def test_fixture_projects_are_not_importable_or_collectable():
    """No package marker and no pytest-collectable file inside the scanned fixture projects."""
    files = [f for f in golden.projects_root().rglob("*") if f.is_file()]
    assert files
    assert not [
        f for f in files if f.name == "__init__.py" or f.name.startswith("test_") or f.name.endswith("_test.py")
    ]
