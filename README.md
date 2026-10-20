# Qwen harness

A small Python learning project for sending requests to a locally served Qwen model, inspecting the HTTP response, and saving selected run data in SQLite. The model server runs separately from this project.

The harness is the Python code around the model. FastAPI exposes one way to call it; the terminal command is another.

## Current state

- `qwen-harness` is a terminal command that sends a fixed chat request to the local vLLM server, measures the completed request, and saves a compact run record.
- `qwen_harness.api` defines a FastAPI `/chat` route. It accepts a JSON object with a required text `message` field, builds vLLM's chat request, and returns vLLM's full JSON reply. Each call sends only the current user message; this route does not yet keep chat history or save a run record.
- The SQLite database is created under `data/` when used. That directory is local runtime data and is excluded from Git.

## Code map

- `src/qwen_harness/cli.py`: terminal entry point.
- `src/qwen_harness/api.py`: incoming HTTP routes.
- `src/qwen_harness/vllm_client.py`: outgoing HTTP request to vLLM.
- `src/qwen_harness/records.py`: selects fields for the compact run record.
- `src/qwen_harness/db/`: opens SQLite, defines the table, and saves or reads run records.

## Current paths through the code

- Postman or a later dashboard → `api.py` validates the incoming message → `vllm_client.py` sends a new HTTP request to vLLM → `api.py` returns vLLM's JSON body.
- `qwen-harness` in a terminal → `cli.py` builds a fixed request → `vllm_client.py` sends it → `records.py` selects run facts → `db/` saves them.

The vLLM URL is a fixed value in `vllm_client.py` for this local setup. It is one chosen configuration value, not a special Python or HTTP name.

## Project environment

Run `uv sync` in the project root to install the dependencies from `pyproject.toml` and `uv.lock`. The vLLM server and its model files are separate and are not part of this repository.
