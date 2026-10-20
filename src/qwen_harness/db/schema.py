import sqlite3


# The colon hints at the parameter type; -> None hints at no return value.
def create_model_runs_table(connection: sqlite3.Connection) -> None:
    """Create the model_runs table using the Connection passed by open_database()."""
    # connection.py passed its open Connection object into this parameter.
    cursor = connection.cursor()
    # This cursor sends the CREATE TABLE statement to SQLite through its connection.
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
