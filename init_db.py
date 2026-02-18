# init_db.py
import sqlite3

def init_db():
    with sqlite3.connect("courses.db") as conn:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    print("✅ Database initialized successfully.")

if __name__ == "__main__":
    init_db()
