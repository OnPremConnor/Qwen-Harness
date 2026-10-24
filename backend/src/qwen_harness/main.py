"""Create the FastAPI app: connect the routers, set up logging, create the tables."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from qwen_harness.db.create_tables import create_tables
from qwen_harness.routers import chat, conversations, pages
from qwen_harness.services.conversation_service import ConversationNotFound

# Uvicorn does not set up logging for our own code, so do it here. Every line our
# code logs then shows a clock time and the module that wrote it.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema.sql creates missing tables on startup; it does not erase saved chats.
    create_tables()
    yield


app = FastAPI(lifespan=lifespan)

# Each router file holds one group of routes; include_router adds them to the app.
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(pages.router)


@app.exception_handler(ConversationNotFound)
async def conversation_not_found(request: Request, error: ConversationNotFound) -> JSONResponse:
    # Services raise this error without knowing about HTTP; this one handler turns it into
    # a 404 reply for every route that can raise it.
    return JSONResponse(status_code=404, content={"detail": "Conversation not found"})
