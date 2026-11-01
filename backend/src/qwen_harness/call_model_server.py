"""Send a question to the model server (today: vLLM running Qwen) and return its reply text."""

import json
import logging
import time

import httpx

# Python names this logger "qwen_harness.call_model_server", the module's import path.
logger = logging.getLogger(__name__)

MODEL_SERVER_URL = "http://127.0.0.1:8000/v1/chat/completions"  # vLLM; port 8000 is set in compose.yaml
MODEL_NAME = "qwen3.8-27b-fp8"  # must match --served-model-name in compose.yaml


class ModelReplyError(Exception):
    """The model server answered, but its reply had no usable content."""


def get_model_answer(question: str) -> str:
    # perf_counter() is a stopwatch: only the difference between two readings means anything.
    started = time.perf_counter()
    # HTTPX sends JSON to the model server; this baseline sends only the current question.
    response = httpx.post(
        MODEL_SERVER_URL,
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": question}],
            "reasoning_effort": "low",
            "stream": False,
        },
        timeout=600.0,  # Seconds to wait for one complete model reply.
    )
    seconds_waiting = time.perf_counter() - started
    # If the server reported an HTTP error, raise an exception for the chat route to handle.
    response.raise_for_status()

    # Try to read the reply text from the JSON structure the server returns.
    try:
        reply_data = response.json()
        content = reply_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        # `except` runs if JSON is invalid or an expected field is missing.
        # `from error` keeps the original parsing problem attached for debugging.
        raise ModelReplyError("The model server returned an unreadable reply") from error

    # The field must contain actual text, not null, another type, or only spaces.
    if not isinstance(content, str) or not content.strip():
        raise ModelReplyError("The model server returned no content")

    # One record of facts about this model call, written as JSON so it can be searched and totaled.
    record = {
        "event": "model_call",
        "seconds_waiting": round(seconds_waiting, 3),
        "http_status": response.status_code,
        "request_bytes": len(response.request.content),
        "response_bytes": len(response.content),
        "question_chars": len(question),
        "content_chars": len(content.strip()),
        "model_requested": MODEL_NAME,
        "id": reply_data["id"],
        "model": reply_data["model"],
        "system_fingerprint": reply_data["system_fingerprint"],
        "finish_reason": reply_data["choices"][0]["finish_reason"],
        "prompt_tokens": reply_data["usage"]["prompt_tokens"],
        "completion_tokens": reply_data["usage"]["completion_tokens"],
        "total_tokens": reply_data["usage"]["total_tokens"],
        "reasoning_tokens": reply_data["usage"]["completion_tokens_details"]["reasoning_tokens"],
    }
    logger.info(json.dumps(record))
    return content.strip()
