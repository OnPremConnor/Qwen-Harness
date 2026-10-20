"""Send outgoing HTTP requests to the separately running vLLM server."""

import httpx

from qwen_harness.settings import VLLM_CHAT_URL, VLLM_TIMEOUT_SECONDS


def send_request(payload: dict) -> httpx.Response:
    """Send a chat payload to the local vLLM server and return its HTTP response."""
    # HTTPX turns this Python dictionary into the outgoing JSON request body.
    return httpx.post(VLLM_CHAT_URL, json=payload, timeout=VLLM_TIMEOUT_SECONDS)
