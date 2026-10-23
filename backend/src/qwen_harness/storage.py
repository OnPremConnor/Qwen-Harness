import sqlite3
from pathlib import Path


def initialize_database(database_path: Path, schema_path: Path) -> None:
    """Create the local file and table from the tracked SQL on API startup."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(schema_path.read_text())
    finally:
        connection.close()


def load_messages(database_path: str | Path, conversation_id: str) -> list[tuple[str, str]]:
    """Return one conversation's (role, content) pairs in insertion order."""
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        )
        return cursor.fetchall()
    finally:
        connection.close()


def save_turn(
    database_path: str | Path, conversation_id: str, user_content: str, assistant_content: str
) -> tuple[int, int]:
    """Save both sides of a successful turn together; return SQLite's row IDs."""
    connection = sqlite3.connect(database_path)
    try:
        # This context commits both INSERTs if they succeed, or rolls both back
        # if either fails. The separate finally block actually closes the file.
        with connection:
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


def load_message_records(database_path: str | Path, conversation_id: str) -> list[dict]:
    """Return saved rows with IDs for the browser, not the vLLM request."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT id, role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def list_conversations(database_path: str | Path) -> list[dict]:
    """Show chats with saved messages, newest activity first."""
    connection = sqlite3.connect(database_path)
    try:
        conversations = connection.execute(
            "SELECT conversation_id, MAX(id) FROM messages "
            "GROUP BY conversation_id ORDER BY MAX(id) DESC"
        ).fetchall()
        summaries = []
        for conversation_id, last_message_id in conversations:
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
