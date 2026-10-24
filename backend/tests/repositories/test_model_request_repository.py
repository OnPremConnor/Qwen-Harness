"""Check the SQL that records one row per model request."""

import sqlite3
import unittest

from qwen_harness.repositories import model_request_repository
from tests.temporary_database import TemporaryDatabaseMixin

RECORD = {
    "conversation_id": "chat-1", "started_at": "2026-10-23T00:00:00+00:00", "status": "ok", "error": None,
    "model": "test-model", "reasoning_effort": "low", "prompt_chars": 5, "prompt_tokens": 1,
    "completion_tokens": 2, "reasoning_tokens": 1, "finish_reason": "stop",
    "seconds_to_first_token": 0.1, "seconds_to_answer": 0.2, "seconds_total": 0.3,
    "reasoning_text": "thinking", "user_message_id": 1, "assistant_message_id": 2,
}


class ModelRequestRepositoryTest(TemporaryDatabaseMixin, unittest.TestCase):
    def test_saves_one_row_and_returns_its_id(self):
        row_id = model_request_repository.save_model_request(RECORD)
        (row,) = self.request_rows()
        self.assertEqual(row_id, row["id"])
        self.assertEqual((row["status"], row["completion_tokens"], row["reasoning_text"]), ("ok", 2, "thinking"))

    def test_a_missing_key_is_an_error_not_a_silent_null(self):
        incomplete = {key: value for key, value in RECORD.items() if key != "status"}
        with self.assertRaises(sqlite3.ProgrammingError):
            model_request_repository.save_model_request(incomplete)
        self.assertEqual(self.request_rows(), [])


if __name__ == "__main__":
    unittest.main()
