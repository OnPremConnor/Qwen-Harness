# Qwen harness

A small backend for learning how an HTTP request reaches a locally served Qwen model. The vLLM model server runs separately in Docker. A dashboard can be added later under `frontend/`; there is no frontend code yet.

## Project map

| Location | Job |
|---|---|
| `backend/` | Python project, dependency lockfile, and its own `.venv/` |
| `backend/schema.sql` | SQL instructions for the local `messages` table |
| `backend/data/` | Local SQLite files; database files are ignored by Git |
| `backend/src/qwen_harness/settings.py` | Fixed local vLLM address, model name, and HTTP timeout |
| `backend/src/qwen_harness/api/main.py` | Creates the FastAPI application and attaches its routes |
| `backend/src/qwen_harness/api/routes/chat.py` | Defines the incoming `POST /chat` route |
| `backend/src/qwen_harness/api/schemas/chat.py` | Defines the required incoming `message` field |
| `backend/src/qwen_harness/harness/chat.py` | Builds vLLM's chat body from that message and reads the reply |
| `backend/src/qwen_harness/harness/vllm_client.py` | Sends the outgoing HTTP request with HTTPX |
| `frontend/` (future) | Dashboard code; it will call this backend over HTTP |

Request flow: caller → API route → harness chat function → vLLM client → vLLM server. The reply travels back through those same Python functions. The current route sends only the caller's latest message and returns vLLM's full JSON reply body. It does not store conversation history or run records.

The schema is tracked in Git; each checkout creates its own local database file. From `backend/`, run `sqlite3 data/chats.db < schema.sql` to create the `messages` table. On this Spark, that file currently contains a small `sqlite-demo` conversation for learning. The FastAPI route does not read or write it yet, so requests to `/chat` still have no saved history. Git ignores the database file.

## Run the backend

From the repository root, enter `backend/` and install its locked Python dependencies:

```bash
cd backend
uv sync
```

`cd` selects the Python project folder. `uv sync` creates or updates `backend/.venv/` from `backend/pyproject.toml` and `backend/uv.lock`. It does not install or start vLLM.

With the separate vLLM server already running, start the FastAPI server:

```bash
uv run uvicorn qwen_harness.api.main:app --host 127.0.0.1 --port 8001
```

`uv run` uses this backend's environment. Uvicorn imports the `app` object from `qwen_harness.api.main`. The host and port make this API reachable only on this machine at `http://127.0.0.1:8001`. Stopping Uvicorn stops this API process, not the vLLM container.

In Postman, send `POST http://127.0.0.1:8001/chat` with a JSON body such as `{"message": "Say hello"}`. FastAPI validates that body, the harness calls vLLM at the fixed address in `settings.py`, and the route returns vLLM's JSON body.
