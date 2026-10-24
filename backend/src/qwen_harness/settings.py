"""Fixed local settings for this learning project."""

from pathlib import Path

# settings.py lives in backend/src/qwen_harness/. These paths point back to
# the checked-out backend and its sibling frontend folder.
BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
DATABASE_PATH = BACKEND_DIR / "data" / "chats.db"
SCHEMA_PATH = BACKEND_DIR / "src" / "qwen_harness" / "db" / "schema.sql"

VLLM_CHAT_URL = "http://127.0.0.1:8000/v1/chat/completions"
VLLM_MODEL = "qwen3.8-27b-fp8"

# Qwen's own default thinking depth is "xhigh" (set in its chat template), which
# can think for thousands of tokens. The page offers low, medium, and xhigh.
DEFAULT_REASONING_EFFORT = "low"

# Longest silence allowed between two pieces of a streamed reply. This covers the
# wait for the first piece (vLLM reading the prompt) and any pause while thinking.
# It is not a limit on the whole reply, which can run as long as pieces keep coming.
VLLM_SILENCE_TIMEOUT_SECONDS = 300
