"""Create the tables from schema.sql when the app starts."""

from qwen_harness.db.connection import connect
from qwen_harness.settings import SCHEMA_PATH


def create_tables() -> None:
    """Run schema.sql; IF NOT EXISTS keeps tables and rows that already exist."""
    connection = connect()
    try:
        connection.executescript(SCHEMA_PATH.read_text())
    finally:
        connection.close()
