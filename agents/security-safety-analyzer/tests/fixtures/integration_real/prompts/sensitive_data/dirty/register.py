import logging

logger = logging.getLogger(__name__)


def register(request):
    logger.info("registration request: %s", request.json)
    return create_account(request.json)
