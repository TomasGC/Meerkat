"""Background jobs run by the Celery worker."""

from celery import Celery, shared_task

app = Celery("worker")
app.config_from_object("celeryconfig")


@app.task
def send_email(to: str, subject: str, body: str) -> None:
    """Send a transactional email."""


@app.task
def process_payment(order_id: int, amount: float) -> bool:
    """Charge an order and return whether it settled."""
    return amount > 0


@shared_task
def rebuild_search_index() -> None:
    """Rebuild the search index from scratch."""
