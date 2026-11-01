"""The JSON shape POST /chat sends back to the browser."""

from pydantic import BaseModel


class ChatResponse(BaseModel):
    # FastAPI sends this field as {"content": "..."} in the HTTP response.
    content: str
