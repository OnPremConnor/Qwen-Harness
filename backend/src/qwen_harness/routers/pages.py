"""The chat page, served at /."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from qwen_harness.settings import FRONTEND_DIR

# include_in_schema=False keeps the page out of the generated /docs API list.
router = APIRouter(include_in_schema=False)


@router.get("/")
def chat_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
