import time

from qwen_harness.db.runs import save_run_record
from qwen_harness.records import make_run_record
from qwen_harness.vllm_client import send_request


def main() -> None:
    # This terminal example fixes the prompt in code. The API route instead
    # gets text from its caller and builds its own vLLM request body.
    vllm_request_body = {
        "model": "qwen3.8-27b-fp8",
        "reasoning_effort": "medium",
        "messages": [
            {"role": "system", "content": "You are FastAPI dev"},
            {"role": "user", "content": "Explain FastAPI in 5 sentences"},
        ],
    }

    # Measure the caller's wait for the complete HTTP reply, not model-only time.
    started = time.perf_counter()
    vllm_response = send_request(vllm_request_body)
    elapsed_seconds = time.perf_counter() - started

    # Pick fields from vLLM's reply and our request, then save those fields.
    run_record = make_run_record(vllm_response, vllm_request_body, elapsed_seconds)
    save_run_record(run_record)  # Opens, commits, and closes a SQLite connection.
    print(run_record)  # This print is terminal output; the save above is persistence.
