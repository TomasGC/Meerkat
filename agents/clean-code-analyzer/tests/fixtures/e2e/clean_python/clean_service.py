# EXPECTED VIOLATIONS: 0 from mechanical checkers

SECONDS_PER_DAY = 86400
MINUTES_PER_DAY = 1440
USER_STATUS_ACTIVE = "active_user"


class UserService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_active_users(self):
        return self._repository.find_by_status(USER_STATUS_ACTIVE)

    def calculate_daily_seconds(self, days: int) -> int:
        return days * SECONDS_PER_DAY


def double_positives(items: list) -> list:
    return [item * 2 for item in items if item > 0]


try:
    connection = db.connect()
except ConnectionError as exc:
    logger.error("DB connection failed: %s", exc)
    raise
