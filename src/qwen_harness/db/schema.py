import sqlite3


def create_model_runs_table(connection: sqlite3.Connection) -> None:
    """Ensure the model_runs table exists on the passed SQLite connection."""
    # open_database() passes its open Connection object into this parameter.
    cursor = connection.cursor()
    # IF NOT EXISTS makes repeated calls safe when the table already exists.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS model_runs (
            request_id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            reasoning_effort TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            elapsed_seconds REAL NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            finish_reason TEXT,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
