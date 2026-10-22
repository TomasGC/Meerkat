import sqlite3


def count_users(db_path):
    connection = sqlite3.connect(db_path)
    rows = connection.execute("SELECT COUNT(*) FROM users").fetchone()
    connection.close()
    return rows[0]
