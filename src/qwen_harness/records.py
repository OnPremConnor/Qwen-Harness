
def make_run_record(response, payload, elapsed_seconds):
    result = response.json()

    return {
        "request_id": result["id"],
        "model": result["model"],
        "reasoning_effort": payload["reasoning_effort"],
        "status_code": response.status_code,
        "elapsed_seconds": elapsed_seconds,
        "prompt_tokens": result["usage"]["prompt_tokens"],
        "completion_tokens": result["usage"]["completion_tokens"],
        "finish_reason": result["choices"][0]["finish_reason"],
    }
