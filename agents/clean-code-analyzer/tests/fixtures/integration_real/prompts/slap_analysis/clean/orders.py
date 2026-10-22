import json


def process_order(order, db):
    validate(order)
    total = compute_total(order["lines"])
    save(db, order["id"], total)
    notify(order["customer"])


def compute_total(lines):
    return sum(line_price(line) for line in lines)


def line_price(line):
    price = line["unit_price_cents"] * line["qty"]
    return price - price * line.get("discount_pct", 0) // 100


def save(db, order_id, total):
    payload = json.dumps({"id": order_id, "total": total}).encode("utf-8")
    db.execute("INSERT INTO orders (id, payload) VALUES (?, ?)", (order_id, payload))


def validate(order):
    if not order.get("lines"):
        raise ValueError("empty order")


def notify(customer):
    print(f"order confirmed for {customer}")
