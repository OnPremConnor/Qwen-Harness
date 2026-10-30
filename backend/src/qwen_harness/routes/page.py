"""Serve the chat page from the repository's frontend folder."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

# This file lives under backend/src/qwen_harness/routes; parents[4] is the repository root.
PAGE = Path(__file__).resolve().parents[4] / "frontend" / "index.html"


@router.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    # FileResponse reads index.html and sends it to the browser.
    return FileResponse(PAGE)
