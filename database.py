import sqlite3
from config import DATABASE_PATH, DATA_DIR


def initialize_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            extension TEXT,
            size INTEGER,
            modified_time REAL,
            content TEXT
        )
        """
    )

    connection.commit()
    connection.close()


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    return sqlite3.connect(DATABASE_PATH)


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized at: {DATABASE_PATH}")