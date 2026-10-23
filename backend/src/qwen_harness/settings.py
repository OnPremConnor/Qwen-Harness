"""Fixed local model settings for this learning project."""

from pathlib import Path

# settings.py lives in backend/src/qwen_harness/. These paths point back to
# the checked-out backend and its sibling frontend folder.
BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
# Vite writes build output here; FastAPI serves these files to the browser.
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FLOW_DIAGRAM_PATH = BACKEND_DIR.parent / "docs" / "request-flow.html"
DATABASE_PATH = BACKEND_DIR / "data" / "chats.db"
SCHEMA_PATH = BACKEND_DIR / "schema.sql"

VLLM_CHAT_URL = "http://127.0.0.1:8000/v1/chat/completions"
VLLM_HEALTH_URL = "http://127.0.0.1:8000/health"
VLLM_MODEL = "qwen3.8-27b-fp8"
VLLM_TIMEOUT_SECONDS = 120

# If set later, this is prepended to each outgoing request. It is not a row
# in the current conversation-history table.
SYSTEM_PROMPT: str | None = None
