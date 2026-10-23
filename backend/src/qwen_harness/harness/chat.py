"""Build one model request from saved history and save a successful turn."""

from uuid import uuid4

from qwen_harness.harness.vllm_client import send_request
from qwen_harness.settings import DATABASE_PATH, SYSTEM_PROMPT, VLLM_MODEL, VLLM_REASONING_EFFORT
from qwen_harness.storage import load_messages, save_turn


class UnknownConversation(Exception):
    """The caller supplied a conversation ID with no saved messages."""


class InvalidModelReply(Exception):
    """vLLM answered, but did not supply assistant text we can save."""


def build_messages(
    saved_rows: list[tuple[str, str]], new_message: str, system_prompt: str | None = None
) -> list[dict[str, str]]:
    """Reshape SQLite tuples into vLLM message dictionaries, in order."""
    # [] creates a new Python list for this request; it does not alter saved rows.
    messages = []
    if system_prompt:
        # A configured system prompt leads the request but is not stored in SQLite.
        messages.append({"role": "system", "content": system_prompt})
    for role, content in saved_rows:
        # Unpack each two-string tuple, then append a new dictionary vLLM expects.
        messages.append({"role": role, "content": content})
    # The current user text has not been saved yet, but the model must see it.
    messages.append({"role": "user", "content": new_message})
    return messages


def generate_chat_completion(message: str, conversation_id: str | None = None) -> dict:
    # The API creates an ID for a new chat; callers reuse the returned ID later.
    active_id = conversation_id if conversation_id is not None else uuid4().hex
    # load_messages opens and closes SQLite before the slower model HTTP call.
    saved_rows = load_messages(DATABASE_PATH, active_id)
    if conversation_id is not None and not saved_rows:
        raise UnknownConversation(active_id)

    # This new dictionary is the body for vLLM, separate from FastAPI's incoming body.
    payload = {
        "model": VLLM_MODEL,
        "messages": build_messages(saved_rows, message, SYSTEM_PROMPT),
    }
    # A process setting can request model thinking depth without changing the dashboard.
    if VLLM_REASONING_EFFORT:
        payload["reasoning_effort"] = VLLM_REASONING_EFFORT
    response = send_request(payload)
    # An unsuccessful HTTP status stops here, so this turn is not saved.
    response.raise_for_status()
    try:
        # HTTPX decodes vLLM's JSON reply into Python dictionaries and lists.
        assistant_content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise InvalidModelReply("Missing assistant content") from error
    if not isinstance(assistant_content, str):
        raise InvalidModelReply("Missing assistant text")
    assistant_content = assistant_content.strip()
    if not assistant_content:
        raise InvalidModelReply("Empty assistant content")

    # A fresh SQLite connection saves both rows only after a valid model reply.
    user_id, assistant_id = save_turn(DATABASE_PATH, active_id, message, assistant_content)
    return {
        "conversation_id": active_id,
        "assistant": assistant_content,
        "user_message_id": user_id,
        "assistant_message_id": assistant_id,
    }
