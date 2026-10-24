"""Describe the JSON body callers send to POST /chat."""

from typing import Literal

from pydantic import BaseModel

from qwen_harness.settings import DEFAULT_REASONING_EFFORT


class ChatRequest(BaseModel):
    """The JSON body the browser (or Postman) sends to POST /chat."""

    # Pydantic requires message text, accepts a missing ID for a new chat, and rejects
    # any reasoning_effort that is not one of the three listed values.
    message: str
    conversation_id: str | None = None
    reasoning_effort: Literal["low", "medium", "xhigh"] = DEFAULT_REASONING_EFFORT
