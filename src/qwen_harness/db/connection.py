import sqlite3
from pathlib import Path

from qwen_harness.db.schema import create_model_runs_table


# This file lives under project/src/qwen_harness/db; parents[3] is project root.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Keep stored runs beside src/, not inside the importable Python package.
DATABASE_PATH = PROJECT_ROOT / "data" / "model-runs.db"


def open_database() -> sqlite3.Connection:
    """Return a new, open connection to this project's SQLite database file."""
    # Create the data/ folder if needed; an existing folder is left alone.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Calling connect opens the file and returns a Connection object.
    connection = sqlite3.connect(DATABASE_PATH)
    # Pass that same object to the schema function so its table exists.
    create_model_runs_table(connection)
    return connection  # The caller closes this object when its work is done.
