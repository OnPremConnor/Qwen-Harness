"""A mixin that gives each test its own throwaway SQLite file."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from qwen_harness.db.create_tables import create_tables


class TemporaryDatabaseMixin:
    """List this first: class MyTest(TemporaryDatabaseMixin, unittest.TestCase)."""

    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database_path = Path(directory.name) / "chats.db"
        # connection.py reads DATABASE_PATH each time connect() runs, so replace its copy of the name.
        database_patch = patch("qwen_harness.db.connection.DATABASE_PATH", self.database_path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        create_tables()

    def request_rows(self) -> list[sqlite3.Row]:
        """Return every model_requests row so a test can check what was recorded."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            return connection.execute("SELECT * FROM model_requests ORDER BY id").fetchall()
        finally:
            connection.close()
