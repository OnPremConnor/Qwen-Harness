"""Pin the JSON the browser receives, and check the page only reads fields that exist."""

import re
import unittest
from pathlib import Path

from qwen_harness.schemas.chat_events import AnswerEvent, DoneEvent, ErrorEvent, ReasoningEvent

PAGE = Path(__file__).parents[3] / "frontend" / "index.html"


class ChatEventsTest(unittest.TestCase):
    def test_wire_format_of_the_small_events(self):
        self.assertEqual(ReasoningEvent(text="a").model_dump_json(), '{"type":"reasoning","text":"a"}')
        self.assertEqual(AnswerEvent(text="b").model_dump_json(), '{"type":"answer","text":"b"}')
        self.assertEqual(
            ErrorEvent(conversation_id="c", message="boom").model_dump_json(),
            '{"type":"error","conversation_id":"c","message":"boom"}',
        )

    def test_every_event_field_the_page_reads_exists(self):
        # Only the page's show() function reads event fields; other "event" variables are DOM events.
        page = PAGE.read_text()
        show_function = page[page.index("function show("):page.index("async function readLines")]
        fields_read = set(re.findall(r"event\.(\w+)", show_function))
        fields_sent = set()
        for model in (ReasoningEvent, AnswerEvent, DoneEvent, ErrorEvent):
            fields_sent |= set(model.model_fields)
        self.assertEqual(fields_read - fields_sent, set())


if __name__ == "__main__":
    unittest.main()
