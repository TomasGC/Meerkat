#!/usr/bin/env python3
"""Celery background tasks."""

from celery import Celery, shared_task
from datetime import datetime

app = Celery('tasks', broker='redis://localhost:6379')


@app.task
def send_email(recipient: str, subject: str, body: str):
    """Send email task.

    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body
    """
    print(f"Sending email to {recipient}: {subject}")
    # Simulate email sending
    return {'status': 'sent', 'timestamp': datetime.now().isoformat()}


@shared_task
def process_payment(order_id: int, amount: float):
    """Process payment task.

    Args:
        order_id: Order ID to process
        amount: Payment amount
    """
    print(f"Processing payment for order {order_id}: ${amount}")
    # Simulate payment processing
    return {'order_id': order_id, 'status': 'completed'}


@app.task(bind=True, max_retries=3)
def generate_report(self, report_type: str, user_id: int):
    """Generate report task with retries.

    Args:
        self: Task instance
        report_type: Type of report to generate
        user_id: User ID requesting report
    """
    try:
        print(f"Generating {report_type} report for user {user_id}")
        # Simulate report generation
        return {'report_id': 123, 'status': 'completed'}
    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e, countdown=60)


@shared_task
def cleanup_old_files(days: int = 30):
    """Cleanup old files task.

    Args:
        days: Number of days to keep files
    """
    print(f"Cleaning up files older than {days} days")
    deleted_count = 0
    # Simulate cleanup
    return {'deleted': deleted_count}
