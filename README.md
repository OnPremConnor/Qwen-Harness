# Qwen Harness

A small local page for sending text to the Qwen model running separately in Docker. This is the code baseline for learning and building the larger [tutoring platform](PROJECT.md).

## What exists now

```text
Browser page → POST /chat → FastAPI → HTTP request to vLLM → content on the page
```

- `frontend/index.html` contains the plain HTML, CSS, and JavaScript page.
- `backend/src/qwen_harness/main.py` creates the app and attaches its route groups.
- `backend/src/qwen_harness/routes/page.py` serves the browser page.
- `backend/src/qwen_harness/routes/chat.py` receives a question, calls the model server, and returns its content.
- `backend/src/qwen_harness/schemas/chat_request.py` describes the JSON the browser sends.
- `backend/src/qwen_harness/schemas/chat_response.py` describes the JSON the browser receives.
- `backend/src/qwen_harness/call_model_server.py` makes the outgoing HTTP request to the separate model server (today vLLM running Qwen), extracts the reply's `content` text, and logs one JSON record per call (see Logging).
- `backend/captured-request-trace.html` shows one real question recorded on 2026-10-31: the actual JSON, headers, sizes, token counts, log lines, and timings at each step, tied to the source line responsible. It is a snapshot pinned to commit `e9abddb` (it predates logging), not a live view; open it in VS Code: right-click the file and choose **Open in Integrated Browser**.
- `backend/pyproject.toml` lists the Python packages; `backend/uv.lock` fixes their resolved versions.

FastAPI's [multiple-file guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/) uses `APIRouter` and `include_router()` for this split. That mechanism is from FastAPI. The folder names `routes/` and `schemas/` are our organizational choice; FastAPI's guide calls the route folder `routers/` and does not require a separate `schemas/` folder. `call_model_server.py` sits beside `main.py` because it is the only outgoing service call so far.

For a question, the browser sends `{"content": "hi"}`. FastAPI builds a `ChatRequest` object and calls `answer_question()` in `routes/chat.py`. That function checks the text and passes a plain Python string to `get_model_answer()` in `call_model_server.py`. HTTPX sends a separate request to vLLM; `get_model_answer()` returns the reply's `content` string. The route puts it in `ChatResponse`, which FastAPI sends as `{"content": "..."}`. No step in that path saves the message.

The page has a New chat button and a disabled Log in button. The sidebar says that history comes later. Each send includes **only the current question**, so Qwen cannot use earlier messages as context yet. Messages remain visible in the open page, but nothing is saved; New chat or a refresh clears that display. The complete answer appears when Qwen finishes.

## Run it

The vLLM container must already be serving Qwen locally. From this repository:

```bash
cd backend
uv sync
uv run uvicorn qwen_harness.main:app --host 127.0.0.1 --port 8001
```

This starts the local chat page. `cd backend` selects the Python project; `uv sync` installs its listed packages into `backend/.venv`; `uv run uvicorn` starts the FastAPI server from that environment. The host address keeps the page on this machine, and the port identifies its local listener. The command does not start the model container or PostgreSQL. Open `http://127.0.0.1:8001/` for the page or `http://127.0.0.1:8001/docs` for FastAPI's generated endpoint description. Stopping Uvicorn stops this page and API but does not stop Qwen's container.

## Python prompt with the project's packages

```bash
cd backend
uv run python
```

This opens Python's interactive prompt (`>>>`) in the project's own environment, so `import httpx` works and `help(httpx)` shows the installed library. `uv run` finds the project by looking for `pyproject.toml` in the current folder and its parents; only `backend/` has one. From the repo root, or with plain `python3`, you get `/usr/bin/python3`, which lacks the packages: `import httpx` fails with `ModuleNotFoundError`. From any folder, `uv run --project ~/projects/qwen-harness/backend python` selects the same environment.

## Logging

Each model call writes one INFO line to the terminal running Uvicorn: the logger name `qwen_harness.call_model_server` followed by a JSON record. `main.py` calls `logging.basicConfig`; without it Python drops INFO lines. The record holds the wait in seconds, HTTP status, request and response sizes in bytes, question and reply lengths in characters, the model requested, and vLLM's own `id`, `model`, `system_fingerprint`, `finish_reason`, `prompt_tokens`, `completion_tokens`, `total_tokens`, and `reasoning_tokens`. It holds no question or reply text. Failed calls are not logged yet. If you redirect Uvicorn's output to a file (for example `> uvicorn.log`; `*.log` is ignored by Git), `grep model_call uvicorn.log` lists the records.

## PostgreSQL is a future learning step

PostgreSQL is installed as an Ubuntu service on this Spark, and a dedicated empty `qwen_harness` database was created during setup. The app does not connect to it and creates no tables. PostgreSQL is not a Python environment package: the database server runs as a separate operating-system service. When we build saved conversations together, we can inspect the server and database, design the tables, and only then add a Python client package and explicit read/write code.

## Next steps

Learn the current request path first, and add logging one slice at a time (failures, request settings, a request id, a log file). Then build conversation context and storage with Connor operating the setup and understanding each piece. Add a real sidebar history and login once those foundations work. The larger product direction remains in [PROJECT.md](PROJECT.md).
