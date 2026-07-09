#!/usr/bin/env python3
"""Message Queue Analyzer for event-driven messaging systems.

Handles detection and analysis of message queue consumers:
- Kafka (Consumer/Producer)
- RabbitMQ (consume/publish)
- AWS SQS/SNS
- Azure Service Bus
"""

import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.constants import MESSAGE_QUEUE_PATTERNS
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


class MessageQueueAnalyzer(BaseEventDrivenAnalyzer):
    """Analyzer for message queue consumers (Kafka, RabbitMQ, SQS, Service Bus)."""

    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if this analyzer can handle message queue projects."""
        return ProjectType.MESSAGE_QUEUE in project_info.project_types

    def extract_entry_points(self, project_path: Path) -> list[EntryPoint]:
        """Extract message queue consumers.

        Returns:
            List of Kafka consumers, RabbitMQ consumers, SQS receivers
        """
        entry_points = []

        # Kafka consumers
        entry_points.extend(self._extract_kafka_consumers(project_path))

        # RabbitMQ consumers
        entry_points.extend(self._extract_rabbitmq_consumers(project_path))

        # AWS SQS receivers
        entry_points.extend(self._extract_sqs_receivers(project_path))

        # Azure Service Bus receivers
        entry_points.extend(self._extract_servicebus_receivers(project_path))

        return entry_points

    def _extract_kafka_consumers(self, project_path: Path) -> list[EntryPoint]:
        """Extract Kafka consumers."""
        entry_points = []

        # Python Kafka consumers
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: KafkaConsumer(...) or @kafka.consumer
            kafka_consumer_pattern = MESSAGE_QUEUE_PATTERNS["kafka_consumer"]
            for match in kafka_consumer_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                # Try to extract consumer variable name
                var_pattern = re.compile(r"(\w+)\s*=\s*.*KafkaConsumer")
                var_match = var_pattern.search(content[max(0, match.start() - 100) : match.start()])
                consumer_name = var_match.group(1) if var_match else "consumer"

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.MESSAGE_CONSUMER,
                        name=f"{consumer_name}.consume",
                        params=[
                            Parameter(
                                name="message",
                                param_type="kafka_message",
                                data_type="ConsumerRecord",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="kafka",
                        metadata={"consumer_type": "kafka_consumer"},
                    )
                )

        # Java/Spring Kafka consumers
        for file_path in walk_files(project_path, ["*.java"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: @KafkaListener
            listener_pattern = re.compile(r"@KafkaListener\s*\([^)]*\)")
            for match in listener_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                # Find method name after annotation
                method_pattern = re.compile(r"public\s+\w+\s+(\w+)\s*\(")
                method_match = method_pattern.search(content, match.end())
                if method_match:
                    method_name = method_match.group(1)

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.MESSAGE_CONSUMER,
                            name=method_name,
                            params=[
                                Parameter(
                                    name="message",
                                    param_type="kafka_message",
                                    data_type="ConsumerRecord",
                                    required=True,
                                )
                            ],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="kafka",
                            metadata={"consumer_type": "kafka_listener"},
                        )
                    )

        # Node.js Kafka consumers
        for file_path in walk_files(project_path, ["*.js", "*.ts"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: consumer.subscribe({...})
            subscribe_pattern = re.compile(r"consumer\.subscribe\s*\(")
            for match in subscribe_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.MESSAGE_CONSUMER,
                        name=f"kafka_consumer_{file_path.stem}_L{line_num}",
                        params=[
                            Parameter(
                                name="message",
                                param_type="kafka_message",
                                data_type="EachMessagePayload",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="kafka",
                        metadata={"consumer_type": "kafka_consumer"},
                    )
                )

        return entry_points

    def _extract_rabbitmq_consumers(self, project_path: Path) -> list[EntryPoint]:
        """Extract RabbitMQ consumers."""
        entry_points = []

        # Python RabbitMQ consumers (pika)
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: channel.consume(...) or channel.basic_consume(...)
            rabbitmq_consume_pattern = MESSAGE_QUEUE_PATTERNS["rabbitmq_consume"]
            for match in rabbitmq_consume_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.MESSAGE_CONSUMER,
                        name=f"rabbitmq_consumer_{file_path.stem}_L{line_num}",
                        params=[
                            Parameter(
                                name="ch",
                                param_type="channel",
                                data_type="Channel",
                                required=True,
                            ),
                            Parameter(
                                name="method",
                                param_type="method",
                                data_type="Basic.Deliver",
                                required=True,
                            ),
                            Parameter(
                                name="properties",
                                param_type="properties",
                                data_type="BasicProperties",
                                required=True,
                            ),
                            Parameter(
                                name="body",
                                param_type="body",
                                data_type="bytes",
                                required=True,
                            ),
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="rabbitmq",
                        metadata={"consumer_type": "basic_consume"},
                    )
                )

        # Java/Spring RabbitMQ consumers
        for file_path in walk_files(project_path, ["*.java"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: @RabbitListener
            listener_pattern = re.compile(r"@RabbitListener\s*\([^)]*\)")
            for match in listener_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                # Find method name
                method_pattern = re.compile(r"public\s+\w+\s+(\w+)\s*\(")
                method_match = method_pattern.search(content, match.end())
                if method_match:
                    method_name = method_match.group(1)

                    entry_points.append(
                        EntryPoint(
                            type=EntryPointType.MESSAGE_CONSUMER,
                            name=method_name,
                            params=[
                                Parameter(
                                    name="message",
                                    param_type="rabbitmq_message",
                                    data_type="Message",
                                    required=True,
                                )
                            ],
                            file_path=format_path_relative(file_path, project_path),
                            line_number=line_num,
                            framework="rabbitmq",
                            metadata={"consumer_type": "rabbit_listener"},
                        )
                    )

        return entry_points

    def _extract_sqs_receivers(self, project_path: Path) -> list[EntryPoint]:
        """Extract AWS SQS receivers."""
        entry_points = []

        # Python SQS receivers (boto3)
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: sqs.receive_message(...) or ReceiveMessageCommand
            sqs_receive_pattern = MESSAGE_QUEUE_PATTERNS["sqs_receive"]
            for match in sqs_receive_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.MESSAGE_CONSUMER,
                        name=f"sqs_receiver_{file_path.stem}_L{line_num}",
                        params=[
                            Parameter(
                                name="message",
                                param_type="sqs_message",
                                data_type="Message",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="aws_sqs",
                        metadata={"consumer_type": "sqs_receiver"},
                    )
                )

        return entry_points

    def _extract_servicebus_receivers(self, project_path: Path) -> list[EntryPoint]:
        """Extract Azure Service Bus receivers."""
        entry_points = []

        # Python Service Bus receivers
        for file_path in walk_files(project_path, ["*.py"]):
            content = read_file_safe(file_path)
            if not content:
                continue

            # Pattern: ServiceBusReceiver(...) or receive_messages(...)
            servicebus_pattern = MESSAGE_QUEUE_PATTERNS["servicebus_receive"]
            for match in servicebus_pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                entry_points.append(
                    EntryPoint(
                        type=EntryPointType.MESSAGE_CONSUMER,
                        name=f"servicebus_receiver_{file_path.stem}_L{line_num}",
                        params=[
                            Parameter(
                                name="message",
                                param_type="servicebus_message",
                                data_type="ServiceBusReceivedMessage",
                                required=True,
                            )
                        ],
                        file_path=format_path_relative(file_path, project_path),
                        line_number=line_num,
                        framework="azure_service_bus",
                        metadata={"consumer_type": "service_bus_receiver"},
                    )
                )

        return entry_points

    def parse_tests(self, project_path: Path) -> list[TestCase]:
        """Parse message queue consumer test files.

        Message queue tests typically:
        - Mock message payloads
        - Test message acknowledgment
        - Validate error handling
        - Check idempotency
        Note: message queue test parsing tracked in #3
        """
        return []
