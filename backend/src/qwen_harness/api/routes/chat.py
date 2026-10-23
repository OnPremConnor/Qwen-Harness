"""Receive chat requests from Postman or a future dashboard."""

import httpx
from fastapi import APIRouter, HTTPException

from qwen_harness.api.schemas.chat import ChatRequest, ChatResponse
from qwen_harness.harness.chat import (
    InvalidModelReply,
    UnknownConversation,
    generate_chat_completion,
)
from qwen_harness.settings import DATABASE_PATH
from qwen_harness.storage import list_conversations, load_message_records

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(chat_request: ChatRequest) -> dict:
    # FastAPI built this ChatRequest from incoming JSON before calling the route.
    message = chat_request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must contain text")
    if chat_request.conversation_id is not None and not chat_request.conversation_id.strip():
        raise HTTPException(status_code=422, detail="conversation_id cannot be empty")
    try:
        # The harness owns history, the model request, and saving a successful turn.
        return generate_chat_completion(message, chat_request.conversation_id)
    except UnknownConversation as error:
        raise HTTPException(status_code=404, detail="Conversation not found") from error
    except (httpx.HTTPError, InvalidModelReply) as error:
        raise HTTPException(status_code=502, detail="Local model request failed") from error


@router.get("/conversations")
def conversations() -> list[dict]:
    # This route reads saved summaries; it never calls the model.
    return list_conversations(DATABASE_PATH)


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str) -> list[dict]:
    # The URL supplies the ID used to select one conversation's SQLite rows.
    messages = load_message_records(DATABASE_PATH, conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages
