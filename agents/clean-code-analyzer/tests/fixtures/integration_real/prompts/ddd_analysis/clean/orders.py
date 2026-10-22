from enum import Enum


class Status(Enum):
    OPEN = "open"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class Order:
    def __init__(self, lines, status=Status.OPEN):
        self._lines = lines
        self._status = status

    def total(self):
        return sum(line.price * line.qty for line in self._lines)

    def cancel(self):
        if self._status is Status.SHIPPED:
            raise ValueError("shipped orders cannot be cancelled")
        self._status = Status.CANCELLED
