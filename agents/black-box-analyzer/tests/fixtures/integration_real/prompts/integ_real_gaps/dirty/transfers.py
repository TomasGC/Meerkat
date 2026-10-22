import sqlite3


def transfer(db_path, source, target, amount):
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, source))
        connection.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, target))
