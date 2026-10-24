"""GET /conversations/{id}/messages: show one saved conversation."""

from fastapi import APIRouter

from qwen_harness.services import conversation_service

# prefix is put in front of every path in this file: "/{conversation_id}/messages"
# becomes "/conversations/{conversation_id}/messages".
router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}/messages")
def conversation_messages(conversation_id: str) -> list[dict]:
    # The URL supplies the ID. The service raises ConversationNotFound when no rows exist,
    # and main.py turns that into HTTP 404.
    return conversation_service.get_messages(conversation_id)
