import httpx


def make_run_record(
    vllm_response: httpx.Response, vllm_request_body: dict, elapsed_seconds: float
) -> dict:
    """Select run facts in memory; db/runs.py handles the separate SQLite save."""
    # .json() reads vLLM's JSON reply body into a Python dictionary.
    result = vllm_response.json()

    return {
        "request_id": result["id"],
        "model": result["model"],
        # This setting came from the outgoing request, not vLLM's reply.
        "reasoning_effort": vllm_request_body["reasoning_effort"],
        "status_code": vllm_response.status_code,
        "elapsed_seconds": elapsed_seconds,
        "prompt_tokens": result["usage"]["prompt_tokens"],
        "completion_tokens": result["usage"]["completion_tokens"],
        # choices is a list; this record selects its first result.
        "finish_reason": result["choices"][0]["finish_reason"],
    }
