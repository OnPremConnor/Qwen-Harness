import sqlite3

from qwen_harness.db.connection import open_database


def save_run_record(run_record: dict) -> None:
    """Insert the selected run facts as one row in the model_runs table."""
    # open_database() returns an open SQLite Connection; this function closes it.
    connection = open_database()
    try:
        cursor = connection.cursor()  # Run SQL through this connection.
        cursor.execute(
            """
            INSERT INTO model_runs (
                request_id, model, reasoning_effort, status_code,
                elapsed_seconds, prompt_tokens, completion_tokens, finish_reason
            ) VALUES (
                :request_id, :model, :reasoning_effort, :status_code,
                :elapsed_seconds, :prompt_tokens, :completion_tokens, :finish_reason
            )
            """,
            run_record,  # SQLite binds each :name to this dictionary's matching key.
        )
        connection.commit()  # Keep the inserted row after this process exits.
    finally:
        connection.close()  # Runs even if the insert or commit raises an error.


def read_run_records() -> list[dict]:
    """Read saved model runs as dictionaries for the future dashboard route."""
    connection = open_database()  # This read gets its own open Connection object.
    connection.row_factory = sqlite3.Row  # Let each row expose its column names.
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM model_runs ORDER BY recorded_at DESC")
        rows = cursor.fetchall()  # Load the rows before closing the connection.
        return [dict(row) for row in rows]  # Convert SQLite rows to Python dictionaries.
    finally:
        connection.close()  # Also runs when the read fails or the function returns.
