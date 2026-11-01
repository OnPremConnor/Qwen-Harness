"""Handle questions sent to POST /chat."""

import httpx
from fastapi import APIRouter, HTTPException

from qwen_harness.call_model_server import ModelReplyError, get_model_answer
from qwen_harness.schemas.chat_request import ChatRequest
from qwen_harness.schemas.chat_response import ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def answer_question(request: ChatRequest) -> ChatResponse:
    # FastAPI made `request` from browser JSON; `request.message` is its text field.
    message = request.message.strip()

    # Whitespace becomes "" after strip(); empty strings are false, so `not` makes this true.
    if not message:
        # `raise` stops this function; FastAPI sends the error response to the browser.
        raise HTTPException(status_code=422, detail="The message must contain text")

    # `try` runs the model call; Python jumps to `except` only if it raises a listed error.
    try:
        content = get_model_answer(message)
    except (httpx.HTTPError, ModelReplyError):
        # A model-server failure becomes a clear HTTP error for the browser.
        raise HTTPException(status_code=502, detail="The model could not complete the reply")

    # This line runs only when the model call returned content successfully.
    return ChatResponse(content=content)
