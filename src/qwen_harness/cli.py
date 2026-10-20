
import time

from qwen_harness.vllm_client import send_request
from qwen_harness.records import make_run_record
from qwen_harness.db.runs import save_run_record


def main():
    payload = {
        "model": "qwen3.8-27b-fp8",
        "reasoning_effort": "medium",
        "messages": [
            {"role": "system", "content": "You are FastAPI dev"},
            {"role": "user", "content": "Explain FastAPI in 5 sentences"},
        ],
    }

    started = time.perf_counter()
    response = send_request(payload)
    elapsed_seconds = time.perf_counter() - started

    # make_run_record returns a dictionary built from the HTTP response and payload.
    run_record = make_run_record(response, payload, elapsed_seconds)
    save_run_record(run_record)  # This function opens and closes its own connection.
    print(run_record)  # Show the saved values in this terminal run.
