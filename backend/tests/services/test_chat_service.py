"""Exercise one chat turn (streaming, saving, failure handling) without a GPU model."""

import sqlite3
import unittest
from unittest.mock import patch

import httpx

from qwen_harness.clients import vllm_client
from qwen_harness.clients.vllm_client import VllmError
from qwen_harness.repositories import model_request_repository
from qwen_harness.repositories.message_repository import load_history, load_message_records
from qwen_harness.services import chat_service
from tests.fake_vllm import (
    USAGE_PIECE,
    fake_vllm,
    piece,
    pretend_vllm_replies_with,
    recorded_stream,
)
from tests.temporary_database import TemporaryDatabaseMixin


class ChatServiceTest(TemporaryDatabaseMixin, unittest.IsolatedAsyncioTestCase):
    async def run_with(self, stream, message="Hi", conversation_id=None, effort="low"):
        with patch.object(vllm_client, "stream_chat", stream):
            return [event async for event in chat_service.run_turn(message, conversation_id, effort)]

    async def test_new_chat_streams_events_and_saves_everything(self):
        sent = []
        stream = fake_vllm(
            piece(reasoning="Think"), piece(content="Hel"), piece(content="lo", finish_reason="stop"),
            USAGE_PIECE, sent=sent,
        )
        events = await self.run_with(stream)

        self.assertEqual([event.type for event in events], ["reasoning", "answer", "answer", "done"])
        done = events[-1]
        self.assertEqual(load_history(done.conversation_id), [("user", "Hi"), ("assistant", "Hello")])
        self.assertEqual((done.user_message_id, done.assistant_message_id), (1, 2))
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
        conversation_id = first[-1].conversation_id
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

        self.assertEqual(events[-1].type, "error")
        self.assertIn("VllmError", events[-1].message)
        self.assertEqual(load_message_records(events[-1].conversation_id), [])
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "error")
        self.assertIn("HTTP 400", row["error"])
        self.assertEqual(row["reasoning_text"], "Partial thought")
        self.assertEqual(row["user_message_id"], None)

    async def test_thinking_without_an_answer_is_an_error_not_an_empty_message(self):
        events = await self.run_with(fake_vllm(piece(reasoning="x", finish_reason="length"), USAGE_PIECE))
        self.assertEqual(events[-1].type, "error")
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "error")
        self.assertIn("finish_reason=length", row["error"])
        self.assertEqual(load_message_records(events[-1].conversation_id), [])

    async def test_a_failed_bookkeeping_row_does_not_hide_the_reply(self):
        stream = fake_vllm(piece(content="Hello"), USAGE_PIECE)
        failing_save = patch.object(
            model_request_repository, "save_model_request",
            side_effect=sqlite3.OperationalError("database is locked"),
        )
        with failing_save, self.assertLogs("qwen_harness.services.chat_service", level="ERROR"):
            events = await self.run_with(stream)

        self.assertEqual(events[-1].type, "done")
        self.assertEqual(load_history(events[-1].conversation_id), [("user", "Hi"), ("assistant", "Hello")])
        self.assertEqual(self.request_rows(), [])

    async def test_stop_records_a_stopped_row_and_saves_no_messages(self):
        stream = fake_vllm(piece(reasoning="a"), piece(content="b"), USAGE_PIECE)
        with patch.object(vllm_client, "stream_chat", stream):
            events = chat_service.run_turn("Hi", "chat-to-stop", "low")
            first = await events.__anext__()
            await events.aclose()  # what happens when the browser disconnects

        self.assertEqual(first.type, "reasoning")
        (row,) = self.request_rows()
        self.assertEqual(row["status"], "stopped")
        self.assertEqual(row["reasoning_text"], "a")
        self.assertEqual(load_message_records("chat-to-stop"), [])


class RecordedStreamTest(TemporaryDatabaseMixin, unittest.IsolatedAsyncioTestCase):
    """Run whole turns against streams that were recorded from the real vLLM server."""

    async def run_recorded(self, name):
        reply = httpx.Response(200, content=recorded_stream(name))
        with pretend_vllm_replies_with(lambda request: reply):
            return [event async for event in chat_service.run_turn("Reply with exactly: pong", None, "low")]

    async def test_a_real_stream_with_an_answer_is_saved_without_its_leading_blank_lines(self):
        events = await self.run_recorded("vllm_stream_with_answer")
        done = events[-1]
        self.assertEqual(done.type, "done")
        self.assertEqual(load_history(done.conversation_id)[-1], ("assistant", "pong"))
        self.assertEqual((done.prompt_tokens, done.completion_tokens, done.reasoning_tokens), (45, 24, 20))

    async def test_a_real_stream_cut_off_while_thinking_is_an_error(self):
        events = await self.run_recorded("vllm_stream_capped_while_thinking")
        self.assertEqual(events[-1].type, "error")
        self.assertIn("finish_reason=length", events[-1].message)
        self.assertEqual(load_message_records(events[-1].conversation_id), [])
        (row,) = self.request_rows()
        self.assertEqual((row["status"], row["reasoning_tokens"]), ("error", 60))


class BuildDoneEventTest(unittest.TestCase):
    def test_speed_is_tokens_divided_by_the_time_after_the_first_piece(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 100, "completion_tokens_details": {"reasoning_tokens": 80}}
        done = chat_service.build_done_event("chat-1", 1, 2, "stop", usage, 2.0, 12.0)
        self.assertEqual(done.tokens_per_second, 10.0)  # 100 tokens / (12.0 s - 2.0 s)
        self.assertEqual(done.reasoning_tokens, 80)

    def test_missing_usage_gives_none_instead_of_a_crash(self):
        done = chat_service.build_done_event("chat-1", 1, 2, None, {}, None, 5.0)
        self.assertEqual((done.completion_tokens, done.reasoning_tokens, done.tokens_per_second), (None, None, None))


if __name__ == "__main__":
    unittest.main()
