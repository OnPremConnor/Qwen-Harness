"""Answer routers' questions about saved conversations (the rules, not the SQL)."""

from qwen_harness.repositories import message_repository


class ConversationNotFound(Exception):
    """No saved message belongs to the requested conversation ID."""


def ensure_exists(conversation_id: str) -> None:
    """Raise ConversationNotFound unless at least one saved message has this ID."""
    if not message_repository.conversation_exists(conversation_id):
        raise ConversationNotFound(conversation_id)


def get_messages(conversation_id: str) -> list[dict]:
    """Return one conversation's saved messages with their row IDs; raise if there are none."""
    messages = message_repository.load_message_records(conversation_id)
    if not messages:
        # The rule "a conversation with no saved messages does not exist" lives here, not in SQL.
        raise ConversationNotFound(conversation_id)
    return messages
