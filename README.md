# Qwen harness

A small local chat app for learning how a browser request reaches a separately served Qwen model and how to measure what the model does. vLLM runs in Docker; FastAPI, SQLite, and one plain HTML page run on the Spark host. The model's reply streams to the page while it is written.

## Project layout

The backend follows the shape in the FastAPI docs ("Bigger Applications"): a package (`qwen_harness`) with a `main.py` that creates the app, and sub-packages (folders with an empty `__init__.py`) that each hold one kind of file. Every file has one job, and no two files share a name.

```
backend/src/qwen_harness/
  main.py            create the app, include the routers, set up logging and tables
  settings.py        paths, vLLM address, model name, default thinking depth, silence limit
  routers/           HTTP in and out: one file per group of URLs
    chat.py            POST /chat (streams JSON lines)
    conversations.py   GET /conversations/{id}/messages
    pages.py           GET / (the chat page)
  schemas/           the JSON shapes in and out (Pydantic)
    chat_schemas.py    ChatRequest: what the browser sends
    chat_events.py     ReasoningEvent, AnswerEvent, DoneEvent, ErrorEvent: what streams back
  services/          the rules: what happens, and in what order
    chat_service.py          one chat turn: history → vLLM → events → save
    conversation_service.py  "does this conversation exist?"
  repositories/      SQL only: one function per query, one file per table
    message_repository.py        the messages table
    model_request_repository.py  the model_requests table
  clients/           calls to other servers
    vllm_client.py     the streamed HTTP request to vLLM
  db/                the database file itself
    connection.py      connect()
    create_tables.py   runs schema.sql at startup
    schema.sql         both tables, with a comment on every column
backend/tests/       mirrors the folders above: routers/, services/, repositories/, clients/, schemas/
backend/tests/fixtures/  replies recorded from the real vLLM server, replayed by the tests
frontend/index.html  the whole chat page: HTML, a little CSS, plain JavaScript, no build step
docs/failure-drills.md  break it on purpose: what each failure looks like in the page, terminal, and database
backend/data/        the local SQLite file (ignored by Git)
```

## The layers

```
browser ─HTTP→ routers ─→ services ─→ repositories ─→ SQLite
                              └─────→ clients ─HTTP→ vLLM
```

Calls only go downward. Each layer knows only its own world:

| Layer | Knows | Does not know |
|---|---|---|
| `routers/` | HTTP: URLs, status codes, JSON | SQL |
| `services/` | the rules and the order of steps | HTTP and SQL details |
| `repositories/` | SQL | HTTP, and the rules |
| `clients/` | how to talk to another server | the database |

A service raises its own error (`ConversationNotFound`, `NoAnswerText`); a router or `main.py` turns it into an HTTP status. A traceback lists files in call order, so it reads routers → services → repositories, and the error class names the layer: `sqlite3.OperationalError` is a repository, `VllmError` is a client, `NoAnswerText` is a service.

## Read the code in this order

1. `main.py`: how the app is put together (a few lines).
2. `routers/chat.py`: the one route that matters; it only handles HTTP.
3. `services/chat_service.py`: `run_turn`, the whole turn. Its docstring lists six numbered steps; the comments inside use the same numbers.
4. `repositories/message_repository.py`, then `repositories/model_request_repository.py`: the SQL.
5. `clients/vllm_client.py`: the streamed HTTP call to vLLM.
6. `db/schema.sql`: both tables, with a comment on every column.
7. `schemas/chat_events.py`, then the script in `frontend/index.html`: what travels to the browser and how the page reads it.
8. `tests/`: each folder tests the matching source folder; `tests/fixtures/` holds real recorded vLLM replies.

## Where new things go

| You add… | It goes in |
|---|---|
| An endpoint | a new file in `routers/` and one `app.include_router(...)` line in `main.py` |
| A table | `db/schema.sql`, plus a new `repositories/<table>_repository.py` |
| Logic that uses it | `services/<name>_service.py` |
| A new request body shape | `schemas/` |
| A call to another outside server | `clients/<name>_client.py` |
| A check several routers share | `dependencies.py` next to `main.py` (the FastAPI docs put it there; none is shared yet) |
| A test | the matching folder under `tests/` |

## What happens on one message

browser → `POST /chat` → `chat_service.run_turn` → SQLite read of the saved history (repository) → Python reshapes `(role, content)` tuples into dictionaries → HTTPX sends JSON with `"stream": true` to vLLM (client) → vLLM replies in pieces → each piece becomes a JSON line (`reasoning`, `answer`, then `done` or `error`) → the page shows them as they arrive. The user and assistant rows are saved only after a good answer. Whatever happens, including a failure or a Stop, one row goes into `model_requests`.

A new chat gets a random UUID from Python. After a finished turn the page puts it in the address bar (`/#<id>`), so a reload can show the saved messages again. SQLite assigns each message its integer `id`; `ORDER BY id` restores the order. `schema.sql` runs at startup and never deletes existing rows.

Qwen's own default thinking depth is `xhigh`, which can think for thousands of tokens even on a simple prompt. The page's Thinking menu defaults to `low`; each request records the level it used.

## Run it

With the separate vLLM server already running, from the repository root:

```bash
cd backend
uv sync
uv run uvicorn qwen_harness.main:app --host 127.0.0.1 --port 8001
```

`uv sync` creates or updates `backend/.venv/` from `pyproject.toml` and `uv.lock`; it does not start vLLM. `uv run` uses that environment, and Uvicorn imports the `app` object from `qwen_harness/main.py`. The host and port make the app reachable only on this machine. Stopping Uvicorn does not stop the vLLM container, and the database file stays on disk.

Open `http://127.0.0.1:8001/` for the chat page, `http://127.0.0.1:8001/docs` for the generated API docs (grouped by each router's tag). Uvicorn's terminal shows one timestamped line when a chat starts and one when it ends, with the status, seconds, and token counts, or the real error.

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

`.tables`, `.schema model_requests`, and `.help` show what exists. Type `.quit` to leave. Pick columns by name instead of `*` on `model_requests`: its `reasoning_text` can be very long.

## Tests

From `backend/`:

```bash
uv run python -m unittest discover -s tests -t . -v
```

The tests use a temporary database and a stand-in model; passing them does not prove vLLM is available. `-t .` makes the `tests/` folders importable as `tests.routers…`, so the test folders can mirror the source folders.

## Calling the API without the page

`POST http://127.0.0.1:8001/chat` with `{"message": "Say hello", "reasoning_effort": "low"}` returns lines of JSON as the reply is written. Add `"conversation_id": "<id from a done line>"` to continue a chat. Bad input is rejected with HTTP 422 or 404 before anything streams. After streaming starts the HTTP status is already 200, so a failure arrives as a line `{"type": "error", ...}`.

To watch the raw lines arrive in a terminal, add `-N` (no buffering) to curl:

```bash
curl -N localhost:8001/chat -H 'Content-Type: application/json' -d '{"message": "Say hi", "reasoning_effort": "low"}'
```

You will see one `{"type":"reasoning",...}` line per piece of thinking, then `answer` lines, then one `done` line with the row IDs and numbers. This request is saved to your real database.

To record a new real stream for a test fixture (for example after upgrading vLLM), talk to vLLM directly and save its raw output:

```bash
curl -sN localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model": "qwen3.8-27b-fp8", "messages": [{"role": "user", "content": "Reply with exactly: pong"}], "stream": true, "stream_options": {"include_usage": true}, "reasoning_effort": "low"}' > backend/tests/fixtures/vllm_stream_with_answer.txt
```

The tests expect the exact numbers in the recordings (for example 24 tokens and the answer `pong`), so update them to match a new recording. If vLLM changed its field names, the replay tests fail and show where.

## Limits

This is a local, single-user app. It does not yet support tool calls, accounts, a conversation list, or safe handling of two sends to the same conversation at once. The `role`/`content` schema stores text chat only. The whole saved history is sent on every turn and is never trimmed, so a very long chat eventually passes the model's 262,144 tokens (context limit); vLLM then rejects each new turn with an HTTP 400, which is recorded in `model_requests`. An answer cut off by a token limit (`finish_reason` of `length`) is still saved as a normal reply. Thinking text is saved in `model_requests`, not in `messages`, so a reload shows the saved messages without it. The streaming field names (`reasoning`, `content`, `usage`) were checked against vLLM 0.28.0.

## Known gaps (to learn and fix later)

- **Blocking SQLite inside async code:** each query takes a few milliseconds and pauses the whole server for that time. Fine for one user; a busier server would run those calls in a thread pool or use an async database driver.
- **No `Depends()`:** modules import what they need directly. FastAPI's usual idiom injects things such as a database session into each route. By default the cleanup code of a `yield` dependency runs after the response has been sent, which matters for a long stream.
- **No migration tool:** `schema.sql` can create a table but cannot change an existing one, so a new column needs a hand-written `ALTER TABLE` until a tool such as Alembic is added.
- **History is never trimmed:** every turn resends the whole conversation.
- **Custom streaming format:** the page reads one JSON object per line. The standard for streamed model replies is Server-Sent Events (`text/event-stream`).
- **`run_turn` is long:** if it grows, a small class could hold the state it collects while the reply streams.
