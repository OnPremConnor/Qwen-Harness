"""Stand-ins for the vLLM server, so tests run without a GPU model."""

from pathlib import Path
from unittest.mock import patch

import httpx

from qwen_harness.clients import vllm_client

# Real replies recorded from the running vLLM 0.28.0 server; see the README to record new ones.
FIXTURES = Path(__file__).parent / "fixtures"


def recorded_stream(name: str) -> bytes:
    """Return the raw bytes of a stream that was recorded from the real vLLM server."""
    return (FIXTURES / f"{name}.txt").read_bytes()


def pretend_vllm_replies_with(handler):
    """Make stream_chat talk to this function instead of the network (httpx's built-in test transport)."""
    real_client = httpx.AsyncClient
    return patch.object(
        vllm_client.httpx, "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )


def piece(reasoning=None, content=None, finish_reason=None) -> dict:
    """Build one hand-made reply piece shaped like the ones vLLM 0.28.0 streams."""
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
