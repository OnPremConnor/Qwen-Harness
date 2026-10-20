# Qwen harness

A small Python learning project for sending requests to a locally served Qwen model, inspecting the HTTP response, and saving selected run data in SQLite. The model server runs separately from this project.

## Current state

- `qwen-harness` is a terminal command that sends a fixed chat request to the local vLLM server, measures the completed request, and saves a compact run record.
- `qwen_harness.api` defines a FastAPI `/chat` route. It currently echoes the JSON request body so we can verify the incoming HTTP path. It does **not** call vLLM yet.
- The SQLite database is created under `data/` when used. That directory is local runtime data and is excluded from Git.

## Code map

- `src/qwen_harness/cli.py`: terminal entry point.
- `src/qwen_harness/api.py`: incoming HTTP routes.
- `src/qwen_harness/vllm_client.py`: outgoing HTTP request to vLLM.
- `src/qwen_harness/records.py`: selects fields for the compact run record.
- `src/qwen_harness/db/`: opens SQLite, defines the table, and saves or reads run records.

## Project environment

Run `uv sync` in the project root to install the dependencies from `pyproject.toml` and `uv.lock`. The vLLM server and its model files are separate and are not part of this repository.
