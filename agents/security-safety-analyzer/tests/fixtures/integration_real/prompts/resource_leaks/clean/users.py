import sqlite3
from contextlib import closing


def count_users(db_path):
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute("SELECT COUNT(*) FROM users").fetchone()
    return rows[0]
