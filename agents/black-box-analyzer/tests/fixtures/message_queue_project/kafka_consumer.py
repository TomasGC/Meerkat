#!/usr/bin/env python3
"""Kafka consumer example."""

from kafka import KafkaConsumer, KafkaProducer
import json


# Consumer setup
consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='user-event-processor'
)


def process_user_event(message):
    """Process user event from Kafka.

    Args:
        message: Kafka message with user event
    """
    event_type = message.value.get('type')
    user_id = message.value.get('userId')

    print(f"Processing {event_type} for user {user_id}")

    if event_type == 'user.created':
        handle_user_created(message.value)
    elif event_type == 'user.updated':
        handle_user_updated(message.value)
    elif event_type == 'user.deleted':
        handle_user_deleted(message.value)


def handle_user_created(data: dict):
    """Handle user created event."""
    print(f"User created: {data}")


def handle_user_updated(data: dict):
    """Handle user updated event."""
    print(f"User updated: {data}")


def handle_user_deleted(data: dict):
    """Handle user deleted event."""
    print(f"User deleted: {data}")


# Consumer loop
def start_consumer():
    """Start Kafka consumer loop."""
    for message in consumer:
        try:
            process_user_event(message)
            consumer.commit()
        except Exception as e:
            print(f"Error processing message: {e}")


# Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


def publish_event(topic: str, event: dict):
    """Publish event to Kafka.

    Args:
        topic: Kafka topic
        event: Event data to publish
    """
    producer.send(topic, value=event)
    producer.flush()
