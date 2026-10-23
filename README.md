# Qwen harness

A local chat dashboard and Python backend for learning how an HTTP request reaches a separately served Qwen model. vLLM runs in Docker; FastAPI, SQLite, and the browser page run on the Spark host.

## Project map

| Location | Job |
|---|---|
| `backend/` | Python project, dependency lockfile, and its own `.venv/` |
| `backend/schema.sql` | SQL instructions for the local `messages` table |
| `backend/data/` | Local SQLite chat file; database files are ignored by Git |
| `backend/src/qwen_harness/settings.py` | Local database and vLLM addresses, model name, and timeout |
| `backend/src/qwen_harness/api/main.py` | Creates FastAPI, runs the SQL schema at startup, serves the built dashboard, flow guide, and health route |
| `backend/src/qwen_harness/api/routes/chat.py` | Receives chat requests and serves saved conversation lists and messages |
| `backend/src/qwen_harness/api/schemas/chat.py` | Defines the incoming `message` and optional `conversation_id` fields |
| `backend/src/qwen_harness/storage.py` | Opens short SQLite connections to read and save messages |
| `backend/src/qwen_harness/harness/chat.py` | Builds ordered vLLM messages from saved rows and saves successful replies |
| `backend/src/qwen_harness/harness/vllm_client.py` | Sends the outgoing HTTP request with HTTPX |
| `frontend/src/App.tsx` | React chat page and browser state; no health request or status cards |
| `frontend/src/api.ts` | Browser HTTP calls and TypeScript shapes for API replies |
| `frontend/src/style.css` | Tailwind CSS entry point |
| `frontend/vite.config.ts` | React and Tailwind build setup; development proxy to FastAPI |
| `docs/request-flow.html` | Clickable, animated source map for a first message and follow-up |

Request flow: browser → FastAPI `/chat` → SQLite read → Python reshapes saved `(role, content)` tuples into dictionaries → HTTPX sends JSON to vLLM → Python extracts assistant text → SQLite saves the user and assistant rows together → FastAPI replies → browser reloads the saved rows. A SQLite connection is not held open while vLLM replies.

When a request has no `conversation_id`, Python generates a random UUID and returns it after a successful reply. The browser sends that ID on later turns. SQLite assigns each message's integer `id` when the row is inserted; `ORDER BY id` reconstructs the saved order. The first user and assistant rows are saved only after vLLM provides valid assistant text. If the model call fails, that turn is not saved. FastAPI executes `schema.sql` on startup to create a missing table without deleting existing rows. Git ignores the database file.

## Run the backend and dashboard

From the repository root, install the frontend's locked dependencies and build its files:

```bash
cd frontend
npm ci
npm run build
```

`cd` selects the frontend project. `npm ci` installs the versions in `package-lock.json` into ignored `node_modules/`. `npm run build` checks TypeScript and writes browser files to ignored `frontend/dist/`. Building files does not start a server or contact vLLM; FastAPI serves the built files when it runs.

From the repository root, enter `backend/` and install its locked Python dependencies:

```bash
cd backend
uv sync
```

`cd` selects the Python project folder. `uv sync` creates or updates `backend/.venv/` from `backend/pyproject.toml` and `backend/uv.lock`. It does not install or start vLLM.

With the separate vLLM server already running, start FastAPI:

```bash
uv run uvicorn qwen_harness.api.main:app --host 127.0.0.1 --port 8001
```

`uv run` uses this backend's environment. Uvicorn imports the `app` object from `qwen_harness.api.main`. The host and port make this API reachable only on this machine at `http://127.0.0.1:8001`. Stopping Uvicorn stops this API process, not the vLLM container; the database file remains on disk.

Open `http://127.0.0.1:8001/` in a browser. React shows saved conversations, SQLite row IDs, and chat replies. The page uses the same HTTP routes available in Postman and at `http://127.0.0.1:8001/docs`. Open `http://127.0.0.1:8001/flow` for a clickable source map of the request. The app's `/health` route remains available for a later lesson; the dashboard does not call it.

For frontend development, run Vite in another terminal after FastAPI is running:

```bash
cd frontend
npm run dev
```

Vite serves source changes at `http://127.0.0.1:5173/`. Its proxy passes `/chat`, `/conversations`, and `/flow` requests to FastAPI at `http://127.0.0.1:8001/`, so the browser can keep using relative URLs. This development server is separate from the built page FastAPI serves; rebuild before expecting source edits to appear on port `8001`.

For a new chat, send `POST http://127.0.0.1:8001/chat` with `{"message": "Say hello"}`. The reply includes `conversation_id`, assistant text, and both saved row IDs. Send a later message with `{"message": "What did I say?", "conversation_id": "<returned ID>"}` to continue the chat. `GET /conversations` lists saved chats; `GET /conversations/<ID>/messages` returns that chat's saved rows.

To exercise the Python history and SQLite save behavior without a running model, run `uv run python -m unittest discover -s tests -v` from `backend/`. The tests use a temporary database and a stand-in model response; passing them does not prove live vLLM availability. The app's `/health` route checks the API, SQLite table, and vLLM health endpoint separately, but the frontend does not display its result.

This is a local, single-user learning app. System-prompt configuration is optional in `settings.py`. Tool calls, streaming, account ownership, and safe handling of concurrent sends to the same conversation are later work; the current `role`/`content` schema stores text chat only.

The Uvicorn process can optionally read `VLLM_REASONING_EFFORT` and `VLLM_TIMEOUT_SECONDS` from its environment. The first adds a `reasoning_effort` field to outgoing model requests; the second changes how long HTTPX waits for a model response. Without those variables, the harness keeps its usual model behavior and 120 seconds (default HTTPX timeout). These settings do not change the React page or the vLLM container.
