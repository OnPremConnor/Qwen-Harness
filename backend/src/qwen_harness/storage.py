import sqlite3
from pathlib import Path


def initialize_database(database_path: Path, schema_path: Path) -> None:
    """Create the local file and table from the tracked SQL on API startup."""
    # mkdir creates the folder; sqlite3.connect creates the .db file if absent.
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        # schema.sql defines the table; IF NOT EXISTS preserves existing chats.
        connection.executescript(schema_path.read_text())
    finally:
        connection.close()


def load_messages(database_path: str | Path, conversation_id: str) -> list[tuple[str, str]]:
    """Return one conversation's (role, content) pairs in insertion order."""
    # connect returns a Connection object; this local name belongs to this call.
    connection = sqlite3.connect(database_path)
    try:
        # The ? placeholder binds the ID as data instead of mixing it into SQL.
        cursor = connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        )
        # fetchall returns a growing list of two-string tuples, one per saved row.
        return cursor.fetchall()
    finally:
        # finally closes the read connection even if the query raises an error.
        connection.close()


def save_turn(
    database_path: str | Path, conversation_id: str, user_content: str, assistant_content: str
) -> tuple[int, int]:
    """Save both sides of a successful turn together; return SQLite's row IDs."""
    connection = sqlite3.connect(database_path)
    try:
        # with connection commits both inserts or rolls both back on an error.
        with connection:
            # execute returns a Cursor; its lastrowid is SQLite's assigned row ID.
            user_cursor = connection.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
                (conversation_id, user_content),
            )
            assistant_cursor = connection.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)",
                (conversation_id, assistant_content),
            )
        # Leaving the with block commits; this tuple contains both assigned IDs.
        return user_cursor.lastrowid, assistant_cursor.lastrowid
    finally:
        # The with block handles the transaction; close releases this connection.
        connection.close()


def load_message_records(database_path: str | Path, conversation_id: str) -> list[dict]:
    """Return saved rows with IDs for the browser, not the vLLM request."""
    connection = sqlite3.connect(database_path)
    # Row objects keep column names, so dict(row) can make browser JSON fields.
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT id, role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        # Each saved Row becomes a new dictionary with id, role, and content.
        return [dict(row) for row in rows]
    finally:
        connection.close()


def list_conversations(database_path: str | Path) -> list[dict]:
    """Show chats with saved messages, newest activity first."""
    connection = sqlite3.connect(database_path)
    try:
        # GROUP BY collects rows with the same conversation ID; MAX finds newest.
        conversations = connection.execute(
            "SELECT conversation_id, MAX(id) FROM messages "
            "GROUP BY conversation_id ORDER BY MAX(id) DESC"
        ).fetchall()
        summaries = []
        for conversation_id, last_message_id in conversations:
            # The earliest user message supplies the sidebar title.
            first_user = connection.execute(
                "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' "
                "ORDER BY id LIMIT 1",
                (conversation_id,),
            ).fetchone()
            summaries.append(
                {
                    "conversation_id": conversation_id,
                    "title": first_user[0] if first_user else "Conversation",
                    "last_message_id": last_message_id,
                }
            )
        return summaries
    finally:
        connection.close()
