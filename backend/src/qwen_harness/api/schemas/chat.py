"""Describe the JSON body callers send to our chat route."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    # Pydantic requires message text and accepts a missing ID for a new chat.
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    # FastAPI checks the outgoing dictionary against these response fields.
    conversation_id: str
    assistant: str
    user_message_id: int
    assistant_message_id: int
