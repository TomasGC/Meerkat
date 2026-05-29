#!/usr/bin/env python3
"""Base analyzer for event-driven systems.

Shared logic for serverless functions, background workers, and message queues.
All event-driven systems share common patterns:
- Asynchronous execution
- Retry mechanisms
- Timeout handling
- Dead letter queues (DLQ)
- Event validation
"""

import sys
from pathlib import Path
from abc import abstractmethod

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.models import (
    EntryPoint,
    Parameter,
    Scenario,
    TestCase,
)

from ..base_analyzer import BaseAnalyzer


class BaseEventDrivenAnalyzer(BaseAnalyzer):
    """Base analyzer for event-driven systems.

    Provides shared scenario generation for:
    - Retry logic (transient failures)
    - Timeout handling (long-running tasks)
    - Dead letter queue (DLQ) scenarios
    - Event validation (schema, format)
    - Async execution patterns
    """

    @abstractmethod
    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract event-driven entry points (handlers, consumers, workers)."""
        pass

    @abstractmethod
    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse event-driven test files."""
        pass

    def generate_scenarios(self, entry_points: list[EntryPoint]) -> list[Scenario]:
        """Generate event-driven scenarios with shared patterns."""
        scenarios = []

        for entry_point in entry_points:
            # Happy path: Valid event
            scenarios.append(
                Scenario(
                    endpoint=entry_point.name,
                    method="EVENT",
                    input_combination={
                        "event": {"type": "valid", "payload": "data"}
                    },
                    expected_output=0,
                    scenario_type="happy_path",
                    description=f"Process valid event in {entry_point.name}",
                )
            )

            # Retry scenarios (transient failures)
            scenarios.extend(self._generate_retry_scenarios(entry_point))

            # Timeout scenarios (long-running tasks)
            scenarios.extend(self._generate_timeout_scenarios(entry_point))

            # DLQ scenarios (unrecoverable failures)
            scenarios.extend(self._generate_dlq_scenarios(entry_point))

            # Event validation scenarios
            scenarios.extend(self._generate_validation_scenarios(entry_point))

            # Async execution scenarios
            scenarios.extend(self._generate_async_scenarios(entry_point))

        return scenarios

    def _generate_retry_scenarios(self, entry_point: EntryPoint) -> list[Scenario]:
        """Generate retry logic scenarios."""
        return [
            # Transient failure (should retry)
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "failure": "transient",
                    "retry_count": 1,
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} with transient failure (retry succeeds)",
            ),
            # Max retries exceeded
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "failure": "transient",
                    "retry_count": 5,
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} max retries exceeded",
            ),
            # Exponential backoff
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "failure": "transient",
                    "backoff": "exponential",
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} exponential backoff retry",
            ),
        ]

    def _generate_timeout_scenarios(self, entry_point: EntryPoint) -> list[Scenario]:
        """Generate timeout handling scenarios."""
        return [
            # Task exceeds timeout
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "long_running"},
                    "timeout": "exceeded",
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} execution timeout",
            ),
            # Task completes within timeout
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "fast"},
                    "timeout": "within_limit",
                },
                expected_output=0,
                scenario_type="happy_path",
                description=f"{entry_point.name} completes within timeout",
            ),
            # Configurable timeout
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "timeout_config": "custom",
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} with custom timeout",
            ),
        ]

    def _generate_dlq_scenarios(self, entry_point: EntryPoint) -> list[Scenario]:
        """Generate dead letter queue (DLQ) scenarios."""
        return [
            # Unrecoverable error (move to DLQ)
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "invalid"},
                    "error": "unrecoverable",
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} unrecoverable error (move to DLQ)",
            ),
            # Poison message (repeatedly fails)
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "poison"},
                    "retry_count": 5,
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} poison message (DLQ after max retries)",
            ),
            # DLQ message processing
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"source": "dlq"},
                    "retry_attempt": True,
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} process message from DLQ",
            ),
        ]

    def _generate_validation_scenarios(self, entry_point: EntryPoint) -> list[Scenario]:
        """Generate event validation scenarios."""
        return [
            # Missing required field
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "invalid", "missing": "required_field"}
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} missing required event field",
            ),
            # Invalid event type
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "unknown"}
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} invalid event type",
            ),
            # Malformed JSON
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": "not_valid_json"
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} malformed event payload",
            ),
            # Schema validation failure
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid", "extra_field": "unexpected"}
                },
                expected_output=1,
                scenario_type="edge_case",
                description=f"{entry_point.name} event schema validation failure",
            ),
        ]

    def _generate_async_scenarios(self, entry_point: EntryPoint) -> list[Scenario]:
        """Generate async execution scenarios."""
        return [
            # Concurrent execution
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "concurrent": True,
                    "concurrent_count": 10,
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} concurrent event processing",
            ),
            # Rate limiting
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "event": {"type": "valid"},
                    "rate_limit": "exceeded",
                },
                expected_output=1,
                scenario_type="error",
                description=f"{entry_point.name} rate limit exceeded",
            ),
            # Batch processing
            Scenario(
                endpoint=entry_point.name,
                method="EVENT",
                input_combination={
                    "events": [{"type": "valid"}, {"type": "valid"}, {"type": "valid"}],
                    "batch_size": 3,
                },
                expected_output=0,
                scenario_type="edge_case",
                description=f"{entry_point.name} batch event processing",
            ),
        ]
