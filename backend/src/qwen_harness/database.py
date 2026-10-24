"""Open the SQLite file and create its tables."""

import sqlite3

from qwen_harness.settings import DATABASE_PATH, SCHEMA_PATH


def connect() -> sqlite3.Connection:
    """Open a new connection to the chat database file; SQLite creates the file if absent."""
    # Every caller opens its own short connection and closes it in a finally block.
    return sqlite3.connect(DATABASE_PATH)


def create_tables() -> None:
    """Run schema.sql on startup; IF NOT EXISTS keeps tables and rows that already exist."""
    # mkdir creates the data/ folder; connect() then creates the .db file inside it.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect()
    try:
        connection.executescript(SCHEMA_PATH.read_text())
    finally:
        connection.close()
