import logging

logger = logging.getLogger(__name__)


def register(request):
    logger.info("registration request received")
    account = create_account(request.json)
    logger.info("registration %s", "succeeded" if account else "failed")
    return account
