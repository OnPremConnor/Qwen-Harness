"""Describe the JSON body callers send to our chat route."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    # The caller chooses text. An absent ID starts a chat; a returned ID
    # continues that chat on a later request.
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    assistant: str
    user_message_id: int
    assistant_message_id: int
