"""Check how vLLM's streamed lines are parsed, using an in-memory stand-in server."""

import unittest

import httpx

from qwen_harness.clients import vllm_client
from qwen_harness.clients.vllm_client import VllmError, parse_stream_line
from tests.fake_vllm import pretend_vllm_replies_with, recorded_stream


class ParseStreamLineTest(unittest.TestCase):
    def test_data_line_becomes_a_dictionary(self):
        self.assertEqual(parse_stream_line('data: {"a": 1}'), {"a": 1})

    def test_done_blank_and_other_lines_are_ignored(self):
        for line in ("data: [DONE]", "", ": keep-alive"):
            self.assertIsNone(parse_stream_line(line))


class StreamChatTest(unittest.IsolatedAsyncioTestCase):
    async def test_yields_each_data_line_as_a_dictionary(self):
        body = b'data: {"a": 1}\n\ndata: {"b": 2}\n\ndata: [DONE]\n\n'
        with pretend_vllm_replies_with(lambda request: httpx.Response(200, content=body)):
            pieces = [piece async for piece in vllm_client.stream_chat({"messages": []})]
        self.assertEqual(pieces, [{"a": 1}, {"b": 2}])

    async def test_replays_a_real_recorded_stream(self):
        body = recorded_stream("vllm_stream_with_answer")
        with pretend_vllm_replies_with(lambda request: httpx.Response(200, content=body)):
            pieces = [piece async for piece in vllm_client.stream_chat({"messages": []})]
        answer = "".join(
            choice["delta"].get("content") or "" for piece in pieces for choice in piece["choices"]
        )
        self.assertEqual(answer, "\n\npong")  # the real stream starts with two blank lines
        self.assertEqual(pieces[-1]["usage"]["completion_tokens"], 24)  # the last piece has no choices

    async def test_an_http_error_raises_vllm_error_with_the_reason(self):
        reply = httpx.Response(400, json={"error": {"message": "too many tokens"}})
        with pretend_vllm_replies_with(lambda request: reply):
            with self.assertRaises(VllmError) as caught:
                [piece async for piece in vllm_client.stream_chat({"messages": []})]
        self.assertIn("HTTP 400", str(caught.exception))
        self.assertIn("too many tokens", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
