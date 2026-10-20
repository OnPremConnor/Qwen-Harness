"""Turn a caller's message into one model request and return its JSON reply."""

from qwen_harness.harness.vllm_client import send_request
from qwen_harness.settings import VLLM_MODEL


def generate_chat_completion(message: str) -> dict:
    # vLLM's chat endpoint expects a model name and a list of message objects.
    payload = {
        "model": VLLM_MODEL,
        "messages": [{"role": "user", "content": message}],
    }
    response = send_request(payload)
    # HTTPX's .json() reads the reply body into Python data. This route returns
    # the full body; it does not yet keep conversation history or save runs.
    return response.json()
