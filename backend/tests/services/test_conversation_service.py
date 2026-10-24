"""Check the rules about which conversations exist."""

import unittest

from qwen_harness.repositories import message_repository
from qwen_harness.services import conversation_service
from qwen_harness.services.conversation_service import ConversationNotFound
from tests.temporary_database import TemporaryDatabaseMixin


class ConversationServiceTest(TemporaryDatabaseMixin, unittest.TestCase):
    def test_unknown_conversation_raises_conversation_not_found(self):
        with self.assertRaises(ConversationNotFound):
            conversation_service.ensure_exists("nope")
        with self.assertRaises(ConversationNotFound):
            conversation_service.get_messages("nope")

    def test_saved_conversation_is_found_with_row_ids(self):
        message_repository.save_turn("chat-1", "Hi", "Hello")
        conversation_service.ensure_exists("chat-1")  # no error means it exists
        messages = conversation_service.get_messages("chat-1")
        self.assertEqual([(row["id"], row["role"], row["content"]) for row in messages],
                         [(1, "user", "Hi"), (2, "assistant", "Hello")])


if __name__ == "__main__":
    unittest.main()
