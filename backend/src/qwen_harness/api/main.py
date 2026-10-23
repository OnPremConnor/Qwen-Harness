"""Create the local API and serve its small browser dashboard."""

import sqlite3
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from qwen_harness.api.routes import chat
from qwen_harness.settings import DATABASE_PATH, FRONTEND_DIR, SCHEMA_PATH, VLLM_HEALTH_URL
from qwen_harness.storage import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema.sql creates the table if missing; it does not erase saved chats.
    initialize_database(DATABASE_PATH, SCHEMA_PATH)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(chat.router)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Report each local boundary separately for the dashboard."""
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            connection.execute("SELECT 1 FROM messages LIMIT 1")
            database = "ready"
        finally:
            connection.close()
    except sqlite3.Error:
        database = "unavailable"

    try:
        response = httpx.get(VLLM_HEALTH_URL, timeout=2)
        model = "ready" if response.is_success else "unavailable"
    except httpx.HTTPError:
        model = "unavailable"
    return {"api": "ready", "database": database, "model": model}
