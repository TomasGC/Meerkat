#!/usr/bin/env python3
"""Live prompt cases: run a checker for real and judge its AI findings alone (#5).

A case is a directory holding one seeded issue:

    <case>/case.json      {"checker", "prompt", "language", "span": [first, last], "issue"}
    <case>/dirty/<file>   the issue, inside the span
    <case>/clean/<file>   the same file with the issue fixed

`run_case` copies one variant to a temporary directory, runs the checker on it
without cache, and keeps the raw AI items apart from the mechanical findings,
before reconciliation merges them. It listens where the checker calls the model
and the reconciliation: in `lib.engine.hybrid`, and in the checker's own module
for the checkers that drive both themselves. A prompt then has to answer with the fields
it asks for, give the dirty file an AI finding in the span, and give the clean
file none there. Elsewhere in the clean file an AI finding is a PromptWarning:
shown in the test report, never a failure.
"""

import json
import re
import shutil
import sys
import tempfile
import warnings
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable
from unittest import mock

import lib.engine.hybrid as _hybrid

PROXIMITY = 3  # the reconciliation window of lib.engine.dedup
_FIELD = re.compile(r'"(\w+)"\s*:')
_CASE_KEYS = {"checker", "prompt", "language", "span", "issue"}


class PromptWarning(UserWarning):
    """An AI finding on a clean twin, away from the fixed issue: a hint, not a failure."""


@dataclass(frozen=True)
class Case:
    name: str
    root: Path
    checker: str
    prompt: str
    language: str
    span: tuple[int, int]
    issue: str
    file: str


@dataclass
class LiveRun:
    result: dict
    ai_items: list[dict] = field(default_factory=list)
    mechanical: list[dict] = field(default_factory=list)
    failed: set[Path] = field(default_factory=set)


def load_cases(root: Path) -> list[Case]:
    """Read every case under root; a malformed case raises instead of testing nothing."""
    cases = []
    for meta_file in sorted(root.glob("*/case.json")):
        case_dir = meta_file.parent
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        missing = _CASE_KEYS - meta.keys()
        if missing:
            raise ValueError(f"{meta_file}: missing {sorted(missing)}")
        names = {variant: sorted(p.name for p in (case_dir / variant).iterdir()) for variant in ("dirty", "clean")}
        if len(names["dirty"]) != 1 or names["dirty"] != names["clean"]:
            raise ValueError(f"{case_dir}: dirty/ and clean/ must hold the same single file, got {names}")
        first, last = meta["span"]
        lines = len((case_dir / "dirty" / names["dirty"][0]).read_text(encoding="utf-8").splitlines())
        if not 1 <= first <= last <= lines:
            raise ValueError(f"{meta_file}: span {meta['span']} is not inside the dirty file's {lines} lines")
        cases.append(
            Case(
                case_dir.name,
                case_dir,
                meta["checker"],
                meta["prompt"],
                meta["language"],
                (first, last),
                meta["issue"],
                names["dirty"][0],
            )
        )
    return cases


def required_fields(prompt_file: Path) -> set[str]:
    """The JSON fields a prompt asks the model for, read from the prompt itself."""
    return set(_FIELD.findall(prompt_file.read_text(encoding="utf-8")))


def _spy_analyze(real: Callable[..., list[dict]], live: LiveRun) -> Callable[..., list[dict]]:
    def analyze(*args, **kwargs):
        kwargs.setdefault("failed", live.failed)
        items = real(*args, **kwargs)
        live.ai_items.extend(items)
        return items

    return analyze


def _spy_dedup(real: Callable[..., list[dict]], live: LiveRun) -> Callable[..., list[dict]]:
    def dedup(ai_violations, existing):
        live.mechanical.extend(existing)
        return real(ai_violations, existing)

    return dedup


@lru_cache(maxsize=None)
def run_case(case: Case, variant: str, run: Callable[..., dict]) -> LiveRun:
    """Run the checker on one variant, once per session, keeping AI items and mechanical findings apart."""
    live = LiveRun(result={})
    seams = [_hybrid, *([sys.modules[run.__module__]] if run.__module__ in sys.modules else [])]
    with ExitStack() as stack, tempfile.TemporaryDirectory() as tmp:
        for module in dict.fromkeys(seams):
            if hasattr(module, "analyze_files_parallel"):
                spy = _spy_analyze(module.analyze_files_parallel, live)
                stack.enter_context(mock.patch.object(module, "analyze_files_parallel", spy))
            if hasattr(module, "drop_near_duplicates"):
                spy = _spy_dedup(module.drop_near_duplicates, live)
                stack.enter_context(mock.patch.object(module, "drop_near_duplicates", spy))
        work = Path(tmp)
        shutil.copy2(case.root / variant / case.file, work / case.file)
        live.result = run(work, case.language, no_cache=True)
    return live


def line_of(item: dict) -> int:
    try:
        return int(item.get("line", 0))
    except (TypeError, ValueError):
        return 0


def in_span(items: list[dict], span: tuple[int, int]) -> list[dict]:
    """Items within the reconciliation window of the span; a line-0 item is about the whole file, never in a span."""
    first, last = span
    return [i for i in items if line_of(i) >= 1 and first - PROXIMITY <= line_of(i) <= last + PROXIMITY]


def outside_span(items: list[dict], span: tuple[int, int]) -> list[dict]:
    inside = in_span(items, span)
    return [i for i in items if i not in inside]


def assert_answer_has_the_fields(live: LiveRun, prompt_file: Path) -> None:
    problems = schema_problems(live, prompt_file)
    assert not problems, problems


def assert_detects(case: Case, live: LiveRun) -> None:
    assert not in_span(live.mechanical, case.span), "fixture invalid: the mechanical layer reports the seeded issue"
    assert in_span(live.ai_items, case.span), f"{case.issue}: no AI finding at {case.span}: {live.ai_items}"


def assert_quiet_once_fixed(case: Case, live: LiveRun) -> None:
    """Fail on an AI finding where the issue was fixed; warn about any other one. No answer is not quiet."""
    assert not live.failed, f"{case.name}: no usable answer for {sorted(f.name for f in live.failed)}"
    for item in outside_span(live.ai_items, case.span):
        warnings.warn(PromptWarning(f"{case.name} clean line {item.get('line')}: {item}"), stacklevel=2)
    assert not in_span(live.ai_items, case.span), f"{case.issue}: still reported once fixed: {live.ai_items}"


def schema_problems(live: LiveRun, prompt_file: Path) -> list[str]:
    """What is wrong with the model's answer: no usable answer, missing fields, leaked <think> text, bad lines."""
    fields = required_fields(prompt_file)
    problems = [f"no usable answer for {f.name}" for f in sorted(live.failed)]
    for item in live.ai_items:
        where = f"item at line {item.get('line')!r}"
        missing = fields - item.keys()
        if missing:
            problems.append(f"{where}: missing {sorted(missing)}")
        if any("<think>" in str(value) for value in item.values()):
            problems.append(f"{where}: <think> text in the answer")
        if line_of(item) < 1:
            problems.append(f"{where}: line is not a positive number")
    return problems
