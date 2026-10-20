import httpx


# Our fixed local vLLM address. Both api.py and cli.py use this target by
# calling send_request(); an edited value takes effect when their process restarts.
VLLM_CHAT_URL = "http://127.0.0.1:8000/v1/chat/completions"


def send_request(vllm_request_body: dict) -> httpx.Response:
    """Send one vLLM chat request and return HTTPX's full Response object."""
    # json= turns the Python dictionary into JSON for the outgoing HTTP body.
    return httpx.post(VLLM_CHAT_URL, json=vllm_request_body, timeout=120)
