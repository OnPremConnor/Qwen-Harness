"""Check the SQL in the messages table functions against a real temporary SQLite file."""

import sqlite3
import unittest

from qwen_harness.repositories import message_repository
from tests.temporary_database import TemporaryDatabaseMixin


class MessageRepositoryTest(TemporaryDatabaseMixin, unittest.TestCase):
    def test_history_comes_back_in_saved_order_for_one_conversation(self):
        message_repository.save_turn("chat-1", "Hi", "Hello")
        message_repository.save_turn("chat-2", "Other", "Chat")
        message_repository.save_turn("chat-1", "What did I say?", "You said Hi.")
        self.assertEqual(
            message_repository.load_history("chat-1"),
            [("user", "Hi"), ("assistant", "Hello"), ("user", "What did I say?"), ("assistant", "You said Hi.")],
        )

    def test_conversation_exists_only_after_a_save(self):
        self.assertFalse(message_repository.conversation_exists("chat-1"))
        message_repository.save_turn("chat-1", "Hi", "Hello")
        self.assertTrue(message_repository.conversation_exists("chat-1"))

    def test_failed_second_insert_rolls_back_first_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            message_repository.save_turn("atomic-demo", "Hi", None)
        self.assertEqual(message_repository.load_history("atomic-demo"), [])


if __name__ == "__main__":
    unittest.main()
