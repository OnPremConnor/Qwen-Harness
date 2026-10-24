"""Open connections to the SQLite file."""

import sqlite3

from qwen_harness.settings import DATABASE_PATH


def connect() -> sqlite3.Connection:
    """Open a new connection to the chat database file; SQLite creates the file if absent."""
    # mkdir creates the data/ folder on first use; sqlite3.connect then creates the .db file in it.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Every caller opens its own short connection and closes it in a finally block.
    return sqlite3.connect(DATABASE_PATH)
