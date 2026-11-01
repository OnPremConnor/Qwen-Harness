"""Send a question to the model server (today: vLLM running Qwen) and return its reply text."""

import httpx

MODEL_SERVER_URL = "http://127.0.0.1:8000/v1/chat/completions"  # vLLM; port 8000 is set in compose.yaml
MODEL_NAME = "qwen3.8-27b-fp8"  # must match --served-model-name in compose.yaml


class ModelReplyError(Exception):
    """The model server answered, but its reply had no usable content."""


def get_model_answer(question: str) -> str:
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
    return content.strip()
