"""Kafka consumer for the orders topic."""

from kafka import KafkaConsumer

consumer = KafkaConsumer("orders", bootstrap_servers="localhost:9092")


def run() -> None:
    """Consume order events until interrupted."""
    for message in consumer:
        handle(message)


def handle(message) -> None:
    """Process a single order event."""
