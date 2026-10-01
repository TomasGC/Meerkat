import hashlib
import pickle
import time

PASSWORD = "hunter2secret"
DEBUG = True


def process_a(items):
    total = 0
    for i in items:
        if i > 0:
            total += i
    return total


def process_b(items):
    total = 0
    for i in items:
        if i > 0:
            total += i
    return total * 2


def kitchen_sink(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
                    else:
                        return 2
                else:
                    return 3
            else:
                return 4
        else:
            return 5
    else:
        return 6


class OrderService:
    def save_order(self, order):
        db_write(order)
        send_email(order.customer_email, "Order confirmed")
        log_audit_event("order_saved", order.id)
        update_inventory(order.items)
        charge_payment(order.total, order.payment_method)


def fingerprint(data):
    return hashlib.md5(data).hexdigest()


def load_session(blob):
    return pickle.loads(blob)


def find_order(cursor, order_id):
    cursor.execute(f"SELECT * FROM orders WHERE id = {order_id}")
    return cursor.fetchone()


def evaluate(expression):
    return eval(expression)


def login(name, password):
    print(f"login attempt for {name}: {password}")
    time.sleep(1)


def read_report(path):
    handle = open(path)
    return handle.read()


def average(total, count):
    try:
        return total / count
    except Exception:
        pass


def build_prompt(user_text):
    return f"Summarize this: {user_text}"
