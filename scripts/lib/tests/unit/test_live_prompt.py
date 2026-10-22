"""Tests for lib.testing.live_prompt: case loading, the AI/mechanical split and the checks."""

import importlib.util
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import lib.ai.model_utils as model_utils
import lib.engine.hybrid as hybrid
from lib import paths
from lib.testing import live_prompt

# the verify.prompt in cca/ssa's prompts/local is a yes/no second opinion (#5), not an
# analysis prompt: it has no JSON schema to assert on, so it's excluded from this list.
_ENGINE_PROMPTS = [
    p
    for p in (
        *(paths.CHECKOUT / "agents/clean-code-analyzer/scripts/prompts/local").glob("*.prompt"),
        *(paths.CHECKOUT / "agents/security-safety-analyzer/scripts/prompts/local").glob("*.prompt"),
        *(
            paths.CHECKOUT / f"agents/black-box-analyzer/scripts/prompts/local/{name}.prompt"
            for name in ("unit_gaps", "integ_mock_gaps", "integ_real_gaps", "e2e_gaps")
        ),
    )
    if p.stem != model_utils.VERIFY_PROMPT
]


def _case(root: Path, dirty="a = 1\nb = 2\nc = 3\n", clean="a = 1\n", span=(2, 2), clean_name="m.py", **drop) -> Path:
    case = root / "solid"
    (case / "dirty").mkdir(parents=True)
    (case / "clean").mkdir()
    (case / "dirty" / "m.py").write_text(dirty)
    (case / "clean" / clean_name).write_text(clean)
    meta = {"checker": "check_x", "prompt": "p", "language": "python", "span": list(span), "issue": "seeded"}
    (case / "case.json").write_text(json.dumps({k: v for k, v in meta.items() if k not in drop}))
    return case


def test_load_cases_reads_each_case(tmp_path):
    _case(tmp_path)

    [case] = live_prompt.load_cases(tmp_path)

    assert (case.name, case.file, case.span, case.checker, case.prompt) == ("solid", "m.py", (2, 2), "check_x", "p")


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"issue": None}, "missing"),
        ({"clean_name": "other.py"}, "same single file"),
        ({"span": (2, 9)}, "not inside"),
    ],
)
def test_load_cases_rejects_a_malformed_case(tmp_path, kwargs, error):
    _case(tmp_path, **kwargs)

    with pytest.raises(ValueError, match=error):
        live_prompt.load_cases(tmp_path)


def test_required_fields_reads_the_json_fields_a_prompt_asks_for(tmp_path):
    prompt = tmp_path / "p.prompt"
    prompt.write_text('Return:\n{{\n  "line": <n>,\n  "severity": "high|low",\n  "violation": "x"\n}}\n')

    assert live_prompt.required_fields(prompt) == {"line", "severity", "violation"}


@pytest.mark.parametrize("prompt", _ENGINE_PROMPTS, ids=lambda p: p.stem)
def test_every_engine_prompt_asks_for_a_line_and_a_severity(prompt):
    assert {"line", "severity"} <= live_prompt.required_fields(prompt)


def test_run_case_keeps_ai_items_apart_from_mechanical_findings(tmp_path):
    [case] = live_prompt.load_cases(_case(tmp_path).parent)
    ai_item = {"line": 3, "severity": "low", "description": "ai", "source_file": "m.py"}

    def run(path, language, no_cache):
        rules = {"python": [(re.compile(r"b = 2"), "mechanical", "low", "fix")]}
        return hybrid.run_hybrid(path, language, "P", "p", rules, no_cache=no_cache)

    with (
        patch.object(hybrid, "check_server_available", return_value=True),
        patch.object(hybrid, "analyze_files_parallel", return_value=[ai_item]) as analyze,
    ):
        live = live_prompt.run_case(case, "dirty", run)

    assert live.ai_items == [ai_item]
    assert [v["line"] for v in live.mechanical] == [2]
    assert analyze.call_args.kwargs["failed"] is live.failed
    assert live.result["success"]


def test_schema_problems_names_each_defect(tmp_path):
    prompt = tmp_path / "p.prompt"
    prompt.write_text('{{ "line": <n>, "severity": "x" }}')
    live = live_prompt.LiveRun(
        result={},
        ai_items=[
            {"line": 4, "severity": "low"},
            {"line": "x", "severity": "low"},
            {"line": 2},
            {"line": 5, "severity": "<think>hm</think> low"},
        ],
        failed={tmp_path / "m.py"},
    )

    problems = live_prompt.schema_problems(live, prompt)

    assert problems == [
        "no usable answer for m.py",
        "item at line 'x': line is not a positive number",
        "item at line 2: missing ['severity']",
        "item at line 5: <think> text in the answer",
    ]


def test_run_case_listens_to_a_checker_that_drives_the_model_itself(tmp_path, monkeypatch):
    [case] = live_prompt.load_cases(_case(tmp_path / "cases").parent)
    source = tmp_path / "own_driver_checker.py"  # a checker with its own driver, like SSA's security checker
    source.write_text(
        "def analyze_files_parallel(files, **kwargs):\n"
        "    return [{'line': 3, 'severity': 'low'}]\n"
        "def drop_near_duplicates(ai, existing):\n"
        "    return ai\n"
        "def run(path, language, no_cache):\n"
        "    mechanical = [{'line': 2}]\n"
        "    ai = analyze_files_parallel(list(path.iterdir()), no_cache=no_cache)\n"
        "    return {'success': True, 'violations': mechanical + drop_near_duplicates(ai, mechanical)}\n"
    )
    spec = importlib.util.spec_from_file_location("own_driver_checker", source)
    checker = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, checker.__name__, checker)
    spec.loader.exec_module(checker)

    live = live_prompt.run_case(case, "dirty", checker.run)

    assert live.ai_items == [{"line": 3, "severity": "low"}]
    assert live.mechanical == [{"line": 2}]


def test_span_checks_use_the_reconciliation_window():
    items = [{"line": n} for n in (1, 6, 10, 14, 15)]

    assert live_prompt.in_span(items, (9, 11)) == [{"line": 6}, {"line": 10}, {"line": 14}]
    assert live_prompt.outside_span(items, (9, 11)) == [{"line": 1}, {"line": 15}]


def _loaded_case(tmp_path):
    [case] = live_prompt.load_cases(_case(tmp_path).parent)
    return case


def test_assert_detects_needs_an_ai_finding_in_the_span(tmp_path):
    case = _loaded_case(tmp_path)

    live_prompt.assert_detects(case, live_prompt.LiveRun(result={}, ai_items=[{"line": 3}]))
    with pytest.raises(AssertionError, match="no AI finding"):
        live_prompt.assert_detects(case, live_prompt.LiveRun(result={}, ai_items=[{"line": 9}]))


def test_assert_detects_rejects_a_seed_the_mechanical_layer_already_reports(tmp_path):
    live = live_prompt.LiveRun(result={}, ai_items=[{"line": 2}], mechanical=[{"line": 2}])

    with pytest.raises(AssertionError, match="fixture invalid"):
        live_prompt.assert_detects(_loaded_case(tmp_path), live)


def test_assert_quiet_once_fixed_warns_away_from_the_fix_and_fails_on_it(tmp_path):
    case = _loaded_case(tmp_path)

    with pytest.warns(live_prompt.PromptWarning, match="clean line 9"):
        live_prompt.assert_quiet_once_fixed(case, live_prompt.LiveRun(result={}, ai_items=[{"line": 9}]))
    with pytest.raises(AssertionError, match="still reported once fixed"):
        live_prompt.assert_quiet_once_fixed(case, live_prompt.LiveRun(result={}, ai_items=[{"line": 2}]))


def test_assert_quiet_once_fixed_fails_when_the_model_gave_no_answer(tmp_path):
    live = live_prompt.LiveRun(result={}, ai_items=[], failed={tmp_path / "m.py"})

    with pytest.raises(AssertionError, match="no usable answer"):
        live_prompt.assert_quiet_once_fixed(_loaded_case(tmp_path), live)


def test_assert_answer_has_the_fields_lists_the_problems(tmp_path):
    prompt = tmp_path / "p.prompt"
    prompt.write_text('{{ "line": <n>, "severity": "x" }}')

    live_prompt.assert_answer_has_the_fields(live_prompt.LiveRun(result={}, ai_items=[]), prompt)
    with pytest.raises(AssertionError, match="missing"):
        live_prompt.assert_answer_has_the_fields(live_prompt.LiveRun(result={}, ai_items=[{"line": 1}]), prompt)


def test_a_whole_file_finding_is_in_no_span():
    items = [{"line": 0}, {"line": 2}]

    assert live_prompt.in_span(items, (1, 3)) == [{"line": 2}]
    assert live_prompt.outside_span(items, (1, 3)) == [{"line": 0}]
