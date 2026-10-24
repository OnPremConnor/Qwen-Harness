"""Create the local web app: three routes, the one-file chat page, and the flow guide."""

import json
import logging
from contextlib import aclosing, asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from qwen_harness.chat_turn import run_turn
from qwen_harness.database import create_tables
from qwen_harness.messages import conversation_exists, load_message_records
from qwen_harness.settings import DEFAULT_REASONING_EFFORT, FLOW_DIAGRAM_PATH, FRONTEND_DIR

# Uvicorn does not set up logging for our own code, so do it here. Every line our
# code logs then shows a clock time and the module that wrote it.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"
)


class ChatRequest(BaseModel):
    """The JSON body the browser (or Postman) sends to POST /chat."""

    # Pydantic requires message text, accepts a missing ID for a new chat, and rejects
    # any reasoning_effort that is not one of the three listed values.
    message: str
    conversation_id: str | None = None
    reasoning_effort: Literal["low", "medium", "xhigh"] = DEFAULT_REASONING_EFFORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema.sql creates missing tables on startup; it does not erase saved chats.
    create_tables()
    yield


app = FastAPI(lifespan=lifespan)


async def to_ndjson(events):
    """Turn each event dictionary into one line of JSON text ("newline-delimited JSON")."""
    # aclosing closes the events generator when the browser disconnects, so the
    # request to vLLM stops and the outcome row is saved right away.
    async with aclosing(events):
        async for event in events:
            yield json.dumps(event) + "\n"


@app.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/flow", include_in_schema=False)
def request_flow() -> FileResponse:
    # This teaching page is a tracked HTML file, separate from the chat page.
    return FileResponse(FLOW_DIAGRAM_PATH)


@app.post("/chat")
async def chat(chat_request: ChatRequest) -> StreamingResponse:
    # FastAPI built this ChatRequest from the incoming JSON before calling this function.
    message = chat_request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must contain text")
    conversation_id = chat_request.conversation_id
    if conversation_id is not None and not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    # The reply is sent as it is produced. Once it starts, the HTTP status is already
    # 200, so a later failure arrives as an {"type": "error"} line instead.
    events = run_turn(message, conversation_id, chat_request.reasoning_effort)
    return StreamingResponse(to_ndjson(events), media_type="application/x-ndjson")


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str) -> list[dict]:
    # The URL supplies the ID used to select one conversation's SQLite rows.
    messages = load_message_records(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages
