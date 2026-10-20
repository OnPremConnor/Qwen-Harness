import sqlite3
from pathlib import Path

from qwen_harness.db.schema import create_model_runs_table


# __file__ is this module's path; parents[3] reaches the project root
# even when the command is run from a different working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# The database is runtime data beside src/, outside the importable package.
DATABASE_PATH = PROJECT_ROOT / "data" / "model-runs.db"


def open_database() -> sqlite3.Connection:
    """Return a new, open connection to this project's SQLite database file."""
    # SQLite needs the parent folder to exist before it can open the file.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # connect opens or creates the database file and returns a Connection object.
    connection = sqlite3.connect(DATABASE_PATH)
    # The schema function uses this same connection to ensure the table exists.
    create_model_runs_table(connection)
    return connection  # The caller owns and must close this open connection.
