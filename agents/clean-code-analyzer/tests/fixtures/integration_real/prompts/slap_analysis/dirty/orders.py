import json


def process_order(order, db):
    validate(order)
    total = 0
    for line in order["lines"]:
        price = line["unit_price_cents"] * line["qty"]
        if line.get("discount_pct"):
            price -= price * line["discount_pct"] // 100
        total += price
    payload = json.dumps({"id": order["id"], "total": total}).encode("utf-8")
    db.execute("INSERT INTO orders (id, payload) VALUES (?, ?)", (order["id"], payload))
    notify(order["customer"])


def validate(order):
    if not order.get("lines"):
        raise ValueError("empty order")


def notify(customer):
    print(f"order confirmed for {customer}")
