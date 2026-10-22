class Order:
    def __init__(self, lines, status):
        self.lines = lines
        self.status = status


class OrderService:
    def total(self, order):
        return sum(line["price"] * line["qty"] for line in order.lines)

    def cancel(self, order):
        if order.status == "shipped":
            raise ValueError("shipped orders cannot be cancelled")
        order.status = "cancelled"
