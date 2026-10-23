"""Create the local API and serve its small browser dashboard."""

import sqlite3
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from qwen_harness.api.routes import chat
from qwen_harness.settings import (
    DATABASE_PATH,
    FLOW_DIAGRAM_PATH,
    FRONTEND_DIST_DIR,
    SCHEMA_PATH,
    VLLM_HEALTH_URL,
)
from qwen_harness.storage import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema.sql creates the table if missing; it does not erase saved chats.
    initialize_database(DATABASE_PATH, SCHEMA_PATH)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(chat.router)
# Vite's built JavaScript and CSS live in dist/assets; the API serves them as files.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets", check_dir=False), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=503, detail="Build the frontend with npm run build")
    return FileResponse(index_path)


@app.get("/flow", include_in_schema=False)
def request_flow() -> FileResponse:
    # This teaching page is a tracked HTML file, separate from the React build.
    return FileResponse(FLOW_DIAGRAM_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    """Report local API, SQLite, and model status for later exercises."""
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
