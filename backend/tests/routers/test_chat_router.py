"""Check the HTTP routes with FastAPI's test client and a stand-in model."""

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from qwen_harness.clients import vllm_client
from qwen_harness.main import app
from tests.fake_vllm import USAGE_PIECE, fake_vllm, piece
from tests.temporary_database import TemporaryDatabaseMixin


class RoutersTest(TemporaryDatabaseMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Entering the client runs the app's startup, which creates the tables.
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_chat_route_streams_json_lines(self):
        stream = fake_vllm(piece(content="Hello"), USAGE_PIECE)
        with patch.object(vllm_client, "stream_chat", stream):
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
        self.assertEqual(missing.json(), {"detail": "Conversation not found"})

    def test_unknown_conversation_messages_return_404(self):
        self.assertEqual(self.client.get("/conversations/nope/messages").status_code, 404)

    def test_chat_page_is_served(self):
        self.assertEqual(self.client.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
