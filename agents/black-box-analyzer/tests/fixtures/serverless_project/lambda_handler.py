#!/usr/bin/env python3
"""AWS Lambda handlers."""

import json


def lambda_handler(event, context):
    """Main Lambda handler for API Gateway.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = event['pathParameters'].get('userId')

        # Process request
        result = process_user_request(user_id, body)

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_user_request(user_id: str, data: dict) -> dict:
    """Process user request."""
    return {
        'userId': user_id,
        'processed': True,
        'data': data
    }


def scheduled_handler(event, context):
    """Handler for scheduled CloudWatch events.

    Args:
        event: CloudWatch event
        context: Lambda context
    """
    print("Running scheduled task")
    cleanup_old_records()
    return {'status': 'completed'}


def cleanup_old_records():
    """Cleanup old database records."""
    pass


def sqs_handler(event, context):
    """Handler for SQS messages.

    Args:
        event: SQS event with records
        context: Lambda context
    """
    for record in event['Records']:
        body = json.loads(record['body'])
        process_message(body)


def process_message(message: dict):
    """Process SQS message."""
    print(f"Processing message: {message}")
