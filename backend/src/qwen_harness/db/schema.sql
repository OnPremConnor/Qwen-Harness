-- SQLite creates each table on startup only when it does not already exist.

-- The saved chat: what gets sent back to the model as history on the next turn.
CREATE TABLE IF NOT EXISTS messages (
    -- SQLite chooses this row ID when Python inserts a message.
    id INTEGER PRIMARY KEY,
    -- Every message in one chat shares the same conversation ID.
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);

-- One row for every model request, including failed and stopped ones.
-- Query it in the sqlite3 shell to see how the model behaved.
CREATE TABLE IF NOT EXISTS model_requests (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    -- UTC time the request began, for example 2026-10-24T00:25:31+00:00.
    started_at TEXT NOT NULL,
    -- ok = answer saved, stopped = the browser disconnected, error = see the error column.
    status TEXT NOT NULL,
    -- The real exception class and message when status is error; otherwise NULL.
    error TEXT,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    -- Characters sent to the model (history plus the new message).
    prompt_chars INTEGER NOT NULL,
    -- Token counts come from vLLM's final usage piece, so they are NULL when the
    -- stream never finished.
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    -- Part of completion_tokens that was thinking rather than answer.
    reasoning_tokens INTEGER,
    -- stop = model finished, length = a token limit cut it off.
    finish_reason TEXT,
    -- Seconds from the start of the request until any text (thinking or answer) arrived.
    seconds_to_first_token REAL,
    -- Seconds until the first answer text, which comes after the thinking.
    seconds_to_answer REAL,
    seconds_total REAL NOT NULL,
    -- The model's thinking text, kept even when the request failed.
    reasoning_text TEXT,
    -- The messages rows saved for this turn; NULL when nothing was saved.
    user_message_id INTEGER,
    assistant_message_id INTEGER
);
