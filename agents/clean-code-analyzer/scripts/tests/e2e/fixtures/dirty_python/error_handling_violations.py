# KNOWN VIOLATIONS: ErrorHandling=3


def fetch_user(user_id):
    try:
        return db.query(user_id)
    except:
        pass  # bare except, swallowed


def save_order(order):
    try:
        db.save(order)
    except Exception:
        pass  # generic, swallowed


def process_payment(amount):
    try:
        gateway.charge(amount)
    except Exception as e:
        error = e  # caught but not logged or raised
