#!/usr/bin/env python3
"""Worker Analyzer for background job systems.

Handles detection and analysis of background workers:
- Celery (Python)
- Sidekiq (Ruby)
- Bull (Node.js)
- asynq (Go)
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.constants import WORKER_PATTERNS
from common.models import (
    EntryPoint,
    EntryPointType,
    Parameter,
    ProjectInfo,
    ProjectType,
    TestCase,
)
from common.utils import (
    format_path_relative,
    read_file_safe,
    walk_files,
)

from .base_event_driven_analyzer import BaseEventDrivenAnalyzer


class WorkerAnalyzer(BaseEventDrivenAnalyzer):
    """Analyzer for background worker systems (Celery, Sidekiq, Bull, asynq)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle background worker projects."""
        return ProjectType.BACKGROUND_WORKER in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract background worker tasks.

        Returns:
            List of Celery tasks, Sidekiq workers, Bull jobs, asynq handlers
        """
        entry_points = []

        # Celery tasks (Python)
        entry_points.extend(self._extract_celery_tasks(project_path))

        # Sidekiq workers (Ruby)
        entry_points.extend(self._extract_sidekiq_workers(project_path))

        # Bull jobs (Node.js)
        entry_points.extend(self._extract_bull_jobs(project_path))

        # asynq handlers (Go)
        entry_points.extend(self._extract_asynq_handlers(project_path))

        return entry_points

    def _extract_celery_tasks(self, project_path: Path) -> list[EntryPoint]:
        """Extract Celery tasks."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: @app.task or @celery.task or @shared_task
            celery_task_pattern = WORKER_PATTERNS["celery_task"]
            for match in celery_task_pattern.finditer(content):
                # Find function name after decorator
                func_pattern = re.compile(r"def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
                func_match = func_pattern.search(content, match.end())
                if func_match:
                    task_name = func_match.group(1)
                    params_str = func_match.group(2)
                    line_num = content[: func_match.start()].count("\n") + 1

                    # Parse parameters
                    params = self._parse_python_params(params_str)

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.BACKGROUND_JOB,
                            name=task_name,
                            params=params,
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="celery",
                            metadata={"worker_type": "task"},
                        )
                    )

        return entry_points

    def _extract_sidekiq_workers(self, project_path: Path) -> list[EntryPoint]:
        """Extract Sidekiq workers."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.rb"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: class WorkerName include Sidekiq::Worker
            sidekiq_worker_pattern = WORKER_PATTERNS["sidekiq_worker"]
            for match in sidekiq_worker_pattern.finditer(content):
                # Extract class name
                class_pattern = re.compile(r"class\s+(\w+)")
                class_match = class_pattern.search(content[: match.start()])
                if class_match:
                    worker_name = class_match.group(1)
                    line_num = content[: class_match.start()].count("\n") + 1

                    # Find perform method
                    perform_pattern = WORKER_PATTERNS["sidekiq_perform"]
                    perform_match = perform_pattern.search(content, match.end())
                    if perform_match:
                        entry_points.append(
                            EntryPoint(
                                type=EntryPointType.BACKGROUND_JOB,
                                name=worker_name,
                                params=[],
                                file_path=format_path_relative(file_path, project_path),
                                line_number=line_num,
                                framework="sidekiq",
                                metadata={"worker_type": "class"},
                            )
                        )

        return entry_points

    def _extract_bull_jobs(self, project_path: Path) -> list[EntryPoint]:
        """Extract Bull queue jobs."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.js", "*.ts"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: queue.process(jobName, handler)
            bull_queue_pattern = WORKER_PATTERNS["bull_queue"]
            for match in bull_queue_pattern.finditer(content):
                # Extract queue and job name
                line_num = content[: match.start()].count("\n") + 1

                # Try to extract queue name
                queue_pattern = re.compile(r"const\s+(\w+)\s*=\s*new\s+Queue")
                queue_match = queue_pattern.search(content[: match.start()])
                queue_name = queue_match.group(1) if queue_match else "queue"

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.BACKGROUND_JOB,
                        name=f"{queue_name}.process",
                        params=[
                            Parameter(
                                name="job",
                                param_type="job",
                                data_type="Job",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="bull",
                        metadata={"worker_type": "processor"},
                    )
                )

        return entry_points

    def _extract_asynq_handlers(self, project_path: Path) -> list[EntryPoint]:
        """Extract asynq handlers."""
        entry_points = []

        for file_path in walk_files(project_path, ["*.go"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: asynq.HandlerFunc(handler)
            asynq_handler_pattern = WORKER_PATTERNS["asynq_handler"]
            for match in asynq_handler_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                # Try to extract handler function name
                func_pattern = re.compile(r"func\s+(\w+)\s*\(")
                func_match = func_pattern.search(content[: match.start()])
                handler_name = func_match.group(1) if func_match else "handler"

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.BACKGROUND_JOB,
                        name=handler_name,
                        params=[
                            Parameter(
                                name="ctx",
                                param_type="context",
                                data_type="context.Context",
                                required=True,
                            ),
                            Parameter(
                                name="task",
                                param_type="task",
                                data_type="*asynq.Task",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="asynq",
                        metadata={"worker_type": "handler"},
                    )
                )

        return entry_points

    def _parse_python_params(self, params_str: str) -> list[Parameter]:
        """Parse Python function parameters."""
        params = []

        if not params_str.strip():
            return params

        # Split by comma (simple parsing)
        for param in params_str.split(","):
            param = param.strip()
            if not param or param == "self":
                continue

            # Parse name: type = default
            parts = re.match(r"(\w+)(?::\s*(\w+))?(?:\s*=\s*(.+))?", param)
            if parts:
                name = parts.group(1)
                param_type = parts.group(2) or "any"
                default = parts.group(3)

                params.append(
                    Parameter(
                        name=name,
                        param_type="arg",
                        data_type=param_type.lower(),
                        required=default is None,
                        default_value=default,
                    )
                )

        return params

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse background worker test files.

        Worker tests typically:
        - Mock task arguments
        - Test retry behavior
        - Validate result storage
        - Check idempotency
        Note: worker test parsing tracked in #3
        """
        return []
