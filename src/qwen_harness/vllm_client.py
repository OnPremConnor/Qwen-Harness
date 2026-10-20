import httpx


VLLM_CHAT_URL = "http://127.0.0.1:8000/v1/chat/completions"


def send_request(payload: dict) -> httpx.Response:
    """Send a chat payload to the local vLLM server and return its HTTP response."""
    return httpx.post(VLLM_CHAT_URL, json=payload, timeout=120)
