import sqlite3

from qwen_harness.db.connection import open_database


def save_run_record(run_record: dict) -> None:
    """Save the run_record dictionary from cli.py as a database row."""
    # cli.py passes in the dictionary returned by make_run_record().
    connection = open_database()  # A fresh Connection object for this call.
    try:
        cursor = connection.cursor()  # This cursor runs SQL on that connection.
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
            run_record,  # Each :name comes from the matching dictionary key.
        )
        connection.commit()  # Make the inserted row persist after Python exits.
    finally:
        connection.close()  # Also runs if execute() or commit() fails.


def read_run_records() -> list[dict]:
    """Return saved model runs as dictionaries for a later dashboard API."""
    connection = open_database()  # A separate Connection object for this read.
    connection.row_factory = sqlite3.Row  # Rows now support column-name lookup.
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM model_runs ORDER BY recorded_at DESC")
        rows = cursor.fetchall()  # Fetch the query's rows before closing.
        return [dict(row) for row in rows]  # Convert SQLite rows to plain Python dictionaries.
    finally:
        connection.close()  # Even returning from try runs this cleanup first.
