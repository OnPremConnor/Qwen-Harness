"""Describe the JSON body callers send to our chat route."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    # The caller chooses the text; our API requires the field name "message".
    message: str
