# Qwen harness

A small local chat app for learning how a browser request reaches a separately served Qwen model and how to measure what the model does. vLLM runs in Docker; FastAPI, SQLite, and one plain HTML page run on the Spark host. The model's reply streams to the page while it is written.

## Project map

Every file has one job, and no two files share a name.

| Location | Job |
|---|---|
| `frontend/index.html` | The whole chat page: HTML, a little CSS, and plain JavaScript. No build step. |
| `backend/src/qwen_harness/main.py` | The FastAPI app: `POST /chat` (streams), `GET /conversations/{id}/messages`, the page at `/`, the flow guide at `/flow` |
| `backend/src/qwen_harness/chat_turn.py` | One chat turn: read history, build the vLLM request, turn reply pieces into events, save the results |
| `backend/src/qwen_harness/vllm_client.py` | Sends the streamed HTTP request to vLLM and yields each reply piece |
| `backend/src/qwen_harness/messages.py` | Saves and loads chat messages (the `messages` table) |
| `backend/src/qwen_harness/model_requests.py` | Saves one row of facts per model request (the `model_requests` table) |
| `backend/src/qwen_harness/database.py` | Opens SQLite connections and creates the tables |
| `backend/src/qwen_harness/settings.py` | Paths, the vLLM address, model name, default thinking depth, and the silence limit |
| `backend/schema.sql` | SQL for both tables, with a comment on every column |
| `backend/tests/test_chat_turn.py` | Tests with a stand-in model; they use a temporary database |
| `backend/data/` | The local SQLite file (ignored by Git) |
| `docs/request-flow.html` | Clickable, animated source map of one request |

## What happens on one message

browser → `POST /chat` → SQLite read of the saved history → Python reshapes `(role, content)` tuples into dictionaries → HTTPX sends JSON with `"stream": true` to vLLM → vLLM replies in pieces → each piece becomes a JSON line (`reasoning`, `answer`, then `done` or `error`) → the page shows them as they arrive. The user and assistant rows are saved only after a good answer. Whatever happens, including a failure or a Stop, one row goes into `model_requests`.

A new chat gets a random UUID from Python. After a finished turn the page puts it in the address bar (`/#<id>`), so a reload can show the saved messages again. SQLite assigns each message its integer `id`; `ORDER BY id` restores the order. `schema.sql` runs at startup and never deletes existing rows.

Qwen's own default thinking depth is `xhigh`, which can think for thousands of tokens even on a simple prompt. The page's Thinking menu defaults to `low`; each request records the level it used.

## Run it

With the separate vLLM server already running, from the repository root:

```bash
cd backend
uv sync
uv run uvicorn qwen_harness.main:app --host 127.0.0.1 --port 8001
```

`uv sync` creates or updates `backend/.venv/` from `pyproject.toml` and `uv.lock`; it does not start vLLM. `uv run` uses that environment, and Uvicorn imports the `app` object from `qwen_harness.main`. The host and port make the app reachable only on this machine. Stopping Uvicorn does not stop the vLLM container, and the database file stays on disk.

Open `http://127.0.0.1:8001/` for the chat page, `http://127.0.0.1:8001/docs` for the generated API docs, and `http://127.0.0.1:8001/flow` for the source map. Uvicorn's terminal shows one timestamped line when a chat starts and one when it ends, with the status, seconds, and token counts, or the real error.

## Look at the data

```bash
cd backend
sqlite3 -readonly data/chats.db
```

Then, at the `sqlite>` prompt:

```sql
SELECT COUNT(*) FROM messages;
SELECT id, status, reasoning_effort, completion_tokens, reasoning_tokens, seconds_total FROM model_requests ORDER BY id DESC LIMIT 5;
```

`.tables`, `.schema model_requests`, and `.help` show what exists. Type `.quit` to leave.

## Tests

From `backend/`:

```bash
uv run python -m unittest discover -s tests -v
```

The tests use a temporary database and a stand-in model; passing them does not prove vLLM is available.

## Calling the API without the page

`POST http://127.0.0.1:8001/chat` with `{"message": "Say hello", "reasoning_effort": "low"}` returns lines of JSON as the reply is written. Add `"conversation_id": "<id from a done line>"` to continue a chat. Bad input is rejected with HTTP 422 or 404 before anything streams. After streaming starts the HTTP status is already 200, so a failure arrives as a line `{"type": "error", ...}`.

## Limits

This is a local, single-user app. It does not yet support tool calls, accounts, a conversation list, or safe handling of two sends to the same conversation at once. The `role`/`content` schema stores text chat only. The whole saved history is sent on every turn and is never trimmed, so a very long chat eventually passes the model's 262,144 tokens (context limit); vLLM then rejects each new turn with an HTTP 400, which is recorded in `model_requests`. An answer cut off by a token limit (`finish_reason` of `length`) is still saved as a normal reply. Thinking text is saved in `model_requests`, not in `messages`, so a reload shows the saved messages without it. The streaming field names (`reasoning`, `content`, `usage`) were checked against vLLM 0.28.0.
