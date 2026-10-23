"""Exercise real SQLite writes and history formation without a GPU model."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from qwen_harness.harness import chat as chat_logic
from qwen_harness.settings import SCHEMA_PATH
from qwen_harness.storage import (
    initialize_database,
    list_conversations,
    load_message_records,
    load_messages,
    save_turn,
)


class ChatFlowTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "chats.db"
        initialize_database(self.database_path, SCHEMA_PATH)
        database_patch = patch.object(chat_logic, "DATABASE_PATH", self.database_path)
        database_patch.start()
        self.addCleanup(database_patch.stop)

    def model_response(self, text: str, status: int = 200) -> httpx.Response:
        return httpx.Response(
            status,
            json={"choices": [{"message": {"content": text}}]},
            request=httpx.Request("POST", "http://127.0.0.1:8000/v1/chat/completions"),
        )

    def test_new_chat_followup_and_saved_history(self):
        outgoing_messages = []

        def fake_model(payload):
            outgoing_messages.append(payload["messages"])
            return self.model_response("Hello!" if len(outgoing_messages) == 1 else "You said Hi.")

        with patch.object(chat_logic, "send_request", side_effect=fake_model):
            first = chat_logic.generate_chat_completion("Hi")
            second = chat_logic.generate_chat_completion("What did I say?", first["conversation_id"])

        self.assertEqual(second["conversation_id"], first["conversation_id"])
        self.assertEqual(
            outgoing_messages,
            [
                [{"role": "user", "content": "Hi"}],
                [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello!"},
                    {"role": "user", "content": "What did I say?"},
                ],
            ],
        )
        rows = load_message_records(self.database_path, first["conversation_id"])
        self.assertEqual([row["role"] for row in rows], ["user", "assistant", "user", "assistant"])
        self.assertEqual([row["id"] for row in rows], sorted(row["id"] for row in rows))
        self.assertEqual(list_conversations(self.database_path)[0]["conversation_id"], first["conversation_id"])

    def test_model_failure_does_not_save_a_partial_turn(self):
        with patch.object(chat_logic, "send_request", return_value=self.model_response("", 503)):
            with self.assertRaises(httpx.HTTPStatusError):
                chat_logic.generate_chat_completion("Hi")
        self.assertEqual(list_conversations(self.database_path), [])

    def test_unknown_conversation_is_rejected_before_model_call(self):
        with patch.object(chat_logic, "send_request") as send_request:
            with self.assertRaises(chat_logic.UnknownConversation):
                chat_logic.generate_chat_completion("Hi", "missing-conversation")
            send_request.assert_not_called()

    def test_failed_second_insert_rolls_back_first_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            save_turn(self.database_path, "atomic-demo", "Hi", None)
        self.assertEqual(load_messages(self.database_path, "atomic-demo"), [])


if __name__ == "__main__":
    unittest.main()
