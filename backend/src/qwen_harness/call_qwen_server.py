"""Send a question to the local vLLM server that runs Qwen."""

import httpx

QWEN_SERVER_URL = "http://127.0.0.1:8000/v1/chat/completions"
QWEN_MODEL = "qwen3.8-27b-fp8"


class QwenReplyError(Exception):
    """The model server answered, but its reply had no usable answer text."""


def get_qwen_answer(question: str) -> str:
    # HTTPX sends JSON to vLLM; this baseline sends only the current question.
    response = httpx.post(
        QWEN_SERVER_URL,
        json={
            "model": QWEN_MODEL,
            "messages": [{"role": "user", "content": question}],
            "reasoning_effort": "low",
            "stream": False,
        },
        timeout=600.0,  # Seconds to wait for one complete model reply.
    )
    # If vLLM reported an HTTP error, raise an exception for the chat route to handle.
    response.raise_for_status()

    # Try to read the answer from the JSON structure vLLM returns.
    try:
        reply_data = response.json()
        answer = reply_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        # `except` runs if JSON is invalid or an expected field is missing.
        # `from error` keeps the original parsing problem attached for debugging.
        raise QwenReplyError("Qwen returned an unreadable reply") from error

    # The field must contain actual text, not null, another type, or only spaces.
    if not isinstance(answer, str) or not answer.strip():
        raise QwenReplyError("Qwen returned no answer text")
    return answer.strip()
