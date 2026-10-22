import logging

logger = logging.getLogger(__name__)


def register(request):
    logger.info("registration request for user id %s", request.json["user_id"])
    return create_account(request.json)
