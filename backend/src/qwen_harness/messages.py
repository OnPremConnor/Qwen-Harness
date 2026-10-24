"""Save and load chat messages (the messages table)."""

from qwen_harness.database import connect


def conversation_exists(conversation_id: str) -> bool:
    """Say whether at least one saved message belongs to this conversation."""
    connection = connect()
    try:
        # LIMIT 1 stops at the first match; we only need to know that one exists.
        row = connection.execute(
            "SELECT 1 FROM messages WHERE conversation_id = ? LIMIT 1", (conversation_id,)
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def load_history(conversation_id: str) -> list[tuple[str, str]]:
    """Return one conversation's (role, content) pairs in the order they were saved."""
    connection = connect()
    try:
        # The ? placeholder binds the ID as data instead of mixing it into the SQL text.
        cursor = connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        )
        # fetchall returns a list of two-string tuples, one per saved row.
        return cursor.fetchall()
    finally:
        connection.close()


def load_message_records(conversation_id: str) -> list[dict]:
    """Return saved rows with their IDs for the browser (not for the vLLM request)."""
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT id, role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        # Name each column so the browser gets {"id": ..., "role": ..., "content": ...}.
        return [
            {"id": row_id, "role": role, "content": content} for row_id, role, content in rows
        ]
    finally:
        connection.close()


def save_turn(conversation_id: str, user_content: str, assistant_content: str) -> tuple[int, int]:
    """Save both sides of a finished turn together; return SQLite's two new row IDs."""
    connection = connect()
    try:
        # "with connection" commits both inserts, or rolls both back if either one fails.
        with connection:
            # execute returns a Cursor; its lastrowid is the ID SQLite just assigned.
            user_cursor = connection.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
                (conversation_id, user_content),
            )
            assistant_cursor = connection.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)",
                (conversation_id, assistant_content),
            )
        return user_cursor.lastrowid, assistant_cursor.lastrowid
    finally:
        connection.close()
