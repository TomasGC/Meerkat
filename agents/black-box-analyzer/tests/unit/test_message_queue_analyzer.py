#!/usr/bin/env python3
"""Tests for analyzers/event_driven/message_queue_analyzer.py: Kafka/RabbitMQ/SQS/Service Bus consumers."""

from pathlib import Path

from analyzers.event_driven.message_queue_analyzer import MessageQueueAnalyzer
from bba.models import EntryPoint, Language, ProjectInfo, ProjectType


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


def test_can_analyze_accepts_only_message_queue_projects(tmp_path):
    assert MessageQueueAnalyzer().can_analyze(_info(tmp_path, ProjectType.MESSAGE_QUEUE))
    assert not MessageQueueAnalyzer().can_analyze(_info(tmp_path, ProjectType.SERVERLESS))


# ── Kafka ─────────────────────────────────────────────────────────────────────


def test_python_kafka_consumer_is_a_message_consumer(tmp_path):
    _write(tmp_path, "consumer.py", "from kafka import KafkaConsumer\n\norders = KafkaConsumer('orders')\n")

    eps = MessageQueueAnalyzer().extract_entry_points(tmp_path)

    assert len(eps) == 1
    consumer = eps[0]
    assert consumer.framework == "kafka"
    assert consumer.line_number == 3
    assert consumer.metadata == {"consumer_type": "kafka_consumer"}
    assert [(p.name, p.data_type) for p in consumer.params] == [("message", "ConsumerRecord")]


def test_python_kafka_consumer_is_named_after_its_variable(tmp_path):
    _write(tmp_path, "consumer.py", "orders = KafkaConsumer('orders')\n")

    names = [ep.name for ep in MessageQueueAnalyzer().extract_entry_points(tmp_path)]

    assert names == ["orders.consume"]


def test_kafka_consumer_without_assignment_gets_default_name(tmp_path):
    _write(tmp_path, "consumer.py", "for msg in KafkaConsumer('orders'):\n    pass\n")

    assert "consumer.consume" in _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))


def test_spring_kafka_listener_uses_annotated_method_name(tmp_path):
    _write(
        tmp_path,
        "OrderListener.java",
        'class OrderListener {\n  @KafkaListener(topics = "orders")\n  public void onOrder(String msg) {}\n}\n',
    )

    eps = _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))

    assert eps["onOrder"].metadata == {"consumer_type": "kafka_listener"}
    assert eps["onOrder"].line_number == 2


def test_listener_annotation_without_public_method_is_ignored(tmp_path):
    _write(tmp_path, "Bad.java", '@KafkaListener(topics = "x")\n@RabbitListener(queues = "y")\nvoid hidden() {}\n')

    assert MessageQueueAnalyzer().extract_entry_points(tmp_path) == []


def test_node_kafka_subscribe_is_named_after_file_and_line(tmp_path):
    _write(tmp_path, "src/worker.ts", "await consumer.connect()\nawait consumer.subscribe({ topic: 'x' })\n")

    eps = _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))

    consumer = eps["kafka_consumer_worker_L2"]
    assert consumer.params[0].data_type == "EachMessagePayload"


# ── RabbitMQ ──────────────────────────────────────────────────────────────────


def test_pika_basic_consume_has_the_four_callback_params(tmp_path):
    _write(tmp_path, "rabbit.py", "import pika\nchannel.basic_consume(queue='q', on_message_callback=cb)\n")

    eps = _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))

    consumer = eps["rabbitmq_consumer_rabbit_L2"]
    assert consumer.framework == "rabbitmq"
    assert [p.name for p in consumer.params] == ["ch", "method", "properties", "body"]


def test_spring_rabbit_listener_uses_annotated_method_name(tmp_path):
    _write(
        tmp_path,
        "Billing.java",
        'class Billing {\n  @RabbitListener(queues = "billing")\n  public void handle(Message m) {}\n}\n',
    )

    eps = _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))

    assert eps["handle"].metadata == {"consumer_type": "rabbit_listener"}
    assert eps["handle"].params[0].param_type == "rabbitmq_message"


# ── SQS and Service Bus ───────────────────────────────────────────────────────


def test_sqs_and_service_bus_receivers(tmp_path):
    _write(
        tmp_path,
        "cloud.py",
        "resp = sqs.receive_message(QueueUrl=url)\n"
        "for m in receiver.receive_messages(max_message_count=5):\n    pass\n",
    )

    eps = _by_name(MessageQueueAnalyzer().extract_entry_points(tmp_path))

    assert eps["sqs_receiver_cloud_L1"].framework == "aws_sqs"
    assert eps["servicebus_receiver_cloud_L2"].framework == "azure_service_bus"
    assert eps["servicebus_receiver_cloud_L2"].params[0].data_type == "ServiceBusReceivedMessage"


def test_empty_sources_yield_nothing(tmp_path):
    for name in ("a.py", "b.java", "c.js", "d.ts"):
        _write(tmp_path, name, "")

    assert MessageQueueAnalyzer().extract_entry_points(tmp_path) == []


def test_parse_tests_returns_no_tests(tmp_path):
    assert MessageQueueAnalyzer().parse_tests(tmp_path) == []


def test_analyze_produces_event_driven_scenarios_for_each_consumer(tmp_path):
    _write(tmp_path, "rabbit.py", "channel.basic_consume(queue='q')\n")

    result = MessageQueueAnalyzer().analyze(tmp_path, _info(tmp_path, ProjectType.MESSAGE_QUEUE))

    assert len(result.entry_points) == 1
    assert result.coverage_matrix.total_scenarios == 17
    assert len(result.risk_assessment) == 17
