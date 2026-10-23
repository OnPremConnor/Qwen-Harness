-- SQLite creates the table on startup only when it does not already exist.
CREATE TABLE IF NOT EXISTS messages (
    -- SQLite chooses this row ID when Python inserts a message.
    id INTEGER PRIMARY KEY,
    -- Every message in one chat shares the same conversation ID.
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);
