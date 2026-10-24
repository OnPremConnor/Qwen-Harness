"""POST /chat: receive a message and stream the reply back as lines of JSON."""

from collections.abc import AsyncIterator
from contextlib import aclosing

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from qwen_harness.schemas.chat_events import ChatEvent
from qwen_harness.schemas.chat_schemas import ChatRequest
from qwen_harness.services import chat_service, conversation_service

# A router is a mini FastAPI app for one group of routes. tags only group them in /docs.
router = APIRouter(tags=["chat"])


async def to_ndjson(events: AsyncIterator[ChatEvent]) -> AsyncIterator[str]:
    """Turn each event into one line of JSON text ("newline-delimited JSON")."""
    # aclosing closes the events generator when the browser disconnects, so the
    # request to vLLM stops and the outcome row is saved right away.
    async with aclosing(events):
        async for event in events:
            yield event.model_dump_json() + "\n"


@router.post("/chat")
async def chat(chat_request: ChatRequest) -> StreamingResponse:
    # FastAPI built this ChatRequest from the incoming JSON before calling this function.
    message = chat_request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must contain text")
    if chat_request.conversation_id is not None:
        # Raises ConversationNotFound; main.py turns that into HTTP 404.
        conversation_service.ensure_exists(chat_request.conversation_id)
    # The reply is sent as it is produced. Once it starts, the HTTP status is already
    # 200, so a later failure arrives as an {"type": "error"} line instead.
    events = chat_service.run_turn(message, chat_request.conversation_id, chat_request.reasoning_effort)
    return StreamingResponse(to_ndjson(events), media_type="application/x-ndjson")
