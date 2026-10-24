"""Exercise streaming, saving, and failure handling without a GPU model."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from qwen_harness import chat_turn, database, main
from qwen_harness.messages import load_history, load_message_records, save_turn
from qwen_harness.vllm_client import VllmError, parse_stream_line


def piece(reasoning=None, content=None, finish_reason=None) -> dict:
    """Build one reply piece shaped like the ones vLLM 0.28.0 streams."""
    delta = {}
    if reasoning is not None:
        delta["reasoning"] = reasoning
    if content is not None:
        delta["content"] = content
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}


# The last piece vLLM sends: token counts and no choices.
USAGE_PIECE = {
    "choices": [],
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 7,
        "completion_tokens_details": {"reasoning_tokens": 4},
    },
}


def fake_vllm(*pieces, error=None, sent=None):
    """Return a stand-in for stream_chat that yields the pieces, then optionally raises."""

    async def stream_chat(payload):
        if sent is not None:
            sent.append(payload)
        for item in pieces:
            yield item
        if error is not None:
            raise error

    return stream_chat


class ChatTurnTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "chats.db"
        database_patch = patch.object(database, "DATABASE_PATH", self.database_path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        database.create_tables()

    def request_rows(self) -> list[sqlite3.Row]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            return connection.execute("SELECT * FROM model_requests ORDER BY id").fetchall()
        finally:
            connection.close()

    async def run_with(self, stream, message="Hi", conversation_id=None, effort="low"):
        with patch.object(chat_turn, "stream_chat", stream):
            return [event async for event in chat_turn.run_turn(message, conversation_id, effort)]

    async def test_new_chat_streams_events_and_saves_everything(self):
        sent = []
        stream = fake_vllm(
            piece(reasoning="Think"), piece(content="Hel"), piece(content="lo", finish_reason="stop"),
            USAGE_PIECE, sent=sent,
        )
        events = await self.run_with(stream)

        self.assertEqual([event["type"] for event in events], ["reasoning", "answer", "answer", "done"])
        done = events[-1]
        self.assertEqual(load_history(done["conversation_id"]), [("user", "Hi"), ("assistant", "Hello")])
        self.assertEqual((done["user_message_id"], done["assistant_message_id"]), (1, 2))
        self.assertEqual(sent[0]["stream"], True)
        self.assertEqual(sent[0]["reasoning_effort"], "low")

        (row,) = self.request_rows()
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["error"], None)
        self.assertEqual((row["prompt_tokens"], row["completion_tokens"], row["reasoning_tokens"]), (12, 7, 4))
        self.assertEqual(row["finish_reason"], "stop")
        self.assertEqual(row["reasoning_text"], "Think")
        self.assertEqual((row["user_message_id"], row["assistant_message_id"]), (1, 2))

    async def test_follow_up_sends_saved_history_to_the_model(self):
        sent = []
        first = await self.run_with(fake_vllm(piece(content="Hello!"), USAGE_PIECE, sent=sent))
        conversation_id = first[-1]["conversation_id"]
        await self.run_with(
            fake_vllm(piece(content="You said Hi."), USAGE_PIECE, sent=sent),
            message="What did I say?", conversation_id=conversation_id,
        )
        self.assertEqual(
            sent[1]["messages"],
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "What did I say?"},
            ],
        )

    async def test_failure_saves_no_messages_but_records_the_real_cause(self):
        stream = fake_vllm(piece(reasoning="Partial thought"), error=VllmError("vLLM replied HTTP 400: bad field"))
        events = await self.run_with(stream)

        self.assertEqual(events[-1]["type"], "error")
        self.assertIn("VllmError", events[-1]["message"])
        self.assertEqual(load_message_records(events[-1]["conversation_id"]), [])
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "error")
        self.assertIn("HTTP 400", row["error"])
        self.assertEqual(row["reasoning_text"], "Partial thought")
        self.assertEqual(row["user_message_id"], None)

    async def test_thinking_without_an_answer_is_an_error_not_an_empty_message(self):
        events = await self.run_with(fake_vllm(piece(reasoning="x", finish_reason="length"), USAGE_PIECE))
        self.assertEqual(events[-1]["type"], "error")
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "error")
        self.assertIn("finish_reason=length", row["error"])
        self.assertEqual(load_message_records(events[-1]["conversation_id"]), [])

    async def test_a_failed_bookkeeping_row_does_not_hide_the_reply(self):
        stream = fake_vllm(piece(content="Hello"), USAGE_PIECE)
        failing_save = patch.object(
            chat_turn, "save_model_request", side_effect=sqlite3.OperationalError("database is locked")
        )
        with failing_save, self.assertLogs("qwen_harness.chat_turn", level="ERROR"):
            events = await self.run_with(stream)

        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(load_history(events[-1]["conversation_id"]), [("user", "Hi"), ("assistant", "Hello")])
        self.assertEqual(self.request_rows(), [])

    async def test_stop_records_a_stopped_row_and_saves_no_messages(self):
        stream = fake_vllm(piece(reasoning="a"), piece(content="b"), USAGE_PIECE)
        with patch.object(chat_turn, "stream_chat", stream):
            events = chat_turn.run_turn("Hi", "chat-to-stop", "low")
            first = await events.__anext__()
            await events.aclose()  # what happens when the browser disconnects

        self.assertEqual(first["type"], "reasoning")
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "stopped")
        self.assertEqual(row["reasoning_text"], "a")
        self.assertEqual(load_message_records("chat-to-stop"), [])

    async def test_failed_second_insert_rolls_back_first_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            save_turn("atomic-demo", "Hi", None)
        self.assertEqual(load_history("atomic-demo"), [])


class ParseStreamLineTest(unittest.TestCase):
    def test_data_line_becomes_a_dictionary(self):
        self.assertEqual(parse_stream_line('data: {"a": 1}'), {"a": 1})

    def test_done_blank_and_other_lines_are_ignored(self):
        for line in ("data: [DONE]", "", ": keep-alive"):
            self.assertIsNone(parse_stream_line(line))


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        database_patch = patch.object(
            database, "DATABASE_PATH", Path(self.temporary_directory.name) / "chats.db"
        )
        database_patch.start()
        self.addCleanup(database_patch.stop)
        # Entering the client runs the app's startup, which creates the tables.
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_chat_route_streams_json_lines(self):
        stream = fake_vllm(piece(content="Hello"), USAGE_PIECE)
        with patch.object(chat_turn, "stream_chat", stream):
            response = self.client.post("/chat", json={"message": "Hi"})
        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(response.status_code, 200)
        self.assertEqual([event["type"] for event in events], ["answer", "done"])
        saved = self.client.get(f"/conversations/{events[-1]['conversation_id']}/messages").json()
        self.assertEqual([row["content"] for row in saved], ["Hi", "Hello"])

    def test_rejections_happen_before_any_streaming(self):
        self.assertEqual(self.client.post("/chat", json={"message": "   "}).status_code, 422)
        self.assertEqual(
            self.client.post("/chat", json={"message": "Hi", "reasoning_effort": "extreme"}).status_code, 422
        )
        missing = self.client.post("/chat", json={"message": "Hi", "conversation_id": "nope"})
        self.assertEqual(missing.status_code, 404)

    def test_unknown_conversation_messages_return_404(self):
        self.assertEqual(self.client.get("/conversations/nope/messages").status_code, 404)


if __name__ == "__main__":
    unittest.main()
