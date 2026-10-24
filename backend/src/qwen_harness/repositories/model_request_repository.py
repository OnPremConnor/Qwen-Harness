"""Save one row of facts about every model request (the model_requests table)."""

from qwen_harness.db.connection import connect

# :name placeholders take their values from the dictionary passed to execute, so the
# SQL stays readable and the dictionary keys must match these names exactly.
INSERT_REQUEST = """
INSERT INTO model_requests (
    conversation_id, started_at, status, error, model, reasoning_effort,
    prompt_chars, prompt_tokens, completion_tokens, reasoning_tokens, finish_reason,
    seconds_to_first_token, seconds_to_answer, seconds_total, reasoning_text,
    user_message_id, assistant_message_id
) VALUES (
    :conversation_id, :started_at, :status, :error, :model, :reasoning_effort,
    :prompt_chars, :prompt_tokens, :completion_tokens, :reasoning_tokens, :finish_reason,
    :seconds_to_first_token, :seconds_to_answer, :seconds_total, :reasoning_text,
    :user_message_id, :assistant_message_id
)
"""


def save_model_request(record: dict) -> int:
    """Insert one row, whatever the outcome of the request, and return its row ID."""
    connection = connect()
    try:
        with connection:
            cursor = connection.execute(INSERT_REQUEST, record)
        return cursor.lastrowid
    finally:
        connection.close()
