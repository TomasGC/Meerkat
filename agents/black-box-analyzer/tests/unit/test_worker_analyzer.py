#!/usr/bin/env python3
"""Tests for analyzers/event_driven/worker_analyzer.py: Celery, Sidekiq, Bull and asynq workers."""

from pathlib import Path

from analyzers.event_driven.worker_analyzer import WorkerAnalyzer
from bba.models import EntryPoint, EntryPointType, Language, ProjectInfo, ProjectType


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _info(root: Path, *types: ProjectType) -> ProjectInfo:
    return ProjectInfo(
        language=Language.PYTHON,
        frameworks=[],
        endpoint_count=0,
        test_file_count=0,
        root_path=str(root),
        project_types=list(types),
        primary_type=types[0] if types else ProjectType.UNKNOWN,
    )


def _by_name(entry_points: list[EntryPoint]) -> dict[str, EntryPoint]:
    return {ep.name: ep for ep in entry_points}


def test_can_analyze_accepts_only_background_workers(tmp_path):
    assert WorkerAnalyzer().can_analyze(_info(tmp_path, ProjectType.BACKGROUND_WORKER))
    assert not WorkerAnalyzer().can_analyze(_info(tmp_path, ProjectType.MESSAGE_QUEUE))


# ── Celery ────────────────────────────────────────────────────────────────────


def test_celery_task_params_skip_self_and_parse_defaults(tmp_path):
    _write(
        tmp_path,
        "tasks.py",
        "@app.task(bind=True)\ndef send_email(self, to: str, retries: int = 3, payload):\n    pass\n",
    )

    task = _by_name(WorkerAnalyzer().extract_entry_points(tmp_path))["send_email"]

    assert task.type == EntryPointType.BACKGROUND_JOB
    assert task.framework == "celery"
    assert task.line_number == 2
    assert [(p.name, p.data_type, p.required, p.default_value) for p in task.params] == [
        ("to", "str", True, None),
        ("retries", "int", False, "3"),
        ("payload", "any", True, None),
    ]


def test_shared_task_without_params(tmp_path):
    _write(tmp_path, "tasks.py", "@shared_task\ndef cleanup():\n    pass\n")

    assert _by_name(WorkerAnalyzer().extract_entry_points(tmp_path))["cleanup"].params == []


def test_celery_decorator_with_no_function_after_it_is_ignored(tmp_path):
    _write(tmp_path, "tasks.py", "x = 1\n@celery.task\n")

    assert WorkerAnalyzer().extract_entry_points(tmp_path) == []


# ── Sidekiq ───────────────────────────────────────────────────────────────────


def test_sidekiq_worker_is_named_after_its_own_class(tmp_path):
    _write(
        tmp_path,
        "app/workers/hard_worker.rb",
        "class HardWorker\n  include Sidekiq::Worker\n\n  def perform(name)\n  end\nend\n",
    )

    eps = WorkerAnalyzer().extract_entry_points(tmp_path)

    assert [ep.name for ep in eps] == ["HardWorker"]


def test_sidekiq_worker_without_perform_method_is_ignored(tmp_path):
    _write(tmp_path, "w.rb", "class Base\nend\nclass Lazy\n  include Sidekiq::Worker\nend\n")

    assert WorkerAnalyzer().extract_entry_points(tmp_path) == []


# ── Bull and asynq ────────────────────────────────────────────────────────────


def test_bull_queue_declaration_is_named_after_its_constant(tmp_path):
    _write(tmp_path, "src/queue.js", "const emailQueue = new Queue('email')\n")

    eps = WorkerAnalyzer().extract_entry_points(tmp_path)

    assert [ep.name for ep in eps] == ["emailQueue.process"]


def test_bull_process_call_is_named_after_the_preceding_queue_constant(tmp_path):
    _write(tmp_path, "src/jobs.ts", "const mailer = new Queue('m')\nqueue.process(handler)\n")

    eps = WorkerAnalyzer().extract_entry_points(tmp_path)

    process = [ep for ep in eps if ep.line_number == 2]
    assert [(ep.name, ep.framework) for ep in process] == [("mailer.process", "bull")]
    assert process[0].params[0].data_type == "Job"


def test_bull_process_call_without_queue_constant_uses_default_name(tmp_path):
    _write(tmp_path, "src/jobs.js", "queue.process(handler)\n")

    assert [ep.name for ep in WorkerAnalyzer().extract_entry_points(tmp_path)] == ["queue.process"]


def test_asynq_handler_is_named_after_preceding_func(tmp_path):
    _write(
        tmp_path,
        "worker.go",
        "package main\n\nfunc handleEmail(ctx context.Context, t *asynq.Task) error { return nil }\n\n"
        'func main() {\n  mux.Handle("email", asynq.HandlerFunc(handleEmail))\n}\n',
    )

    eps = WorkerAnalyzer().extract_entry_points(tmp_path)

    assert [(ep.name, ep.line_number, ep.framework) for ep in eps] == [("main", 6, "asynq")]
    assert [p.data_type for p in eps[0].params] == ["context.Context", "*asynq.Task"]


def test_asynq_handler_without_any_func_uses_default_name(tmp_path):
    _write(tmp_path, "reg.go", "var h = asynq.HandlerFunc(x)\n")

    assert [ep.name for ep in WorkerAnalyzer().extract_entry_points(tmp_path)] == ["handler"]


def test_empty_sources_yield_nothing(tmp_path):
    for name in ("a.py", "b.rb", "c.js", "d.go"):
        _write(tmp_path, name, "")

    assert WorkerAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_tests_returns_no_tests(tmp_path):
    assert WorkerAnalyzer().parse_tests(tmp_path) == []
