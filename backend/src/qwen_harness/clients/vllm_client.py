"""Send one streamed chat request to the separately running vLLM server."""

import json
from collections.abc import AsyncIterator

import httpx

from qwen_harness.settings import VLLM_CHAT_URL, VLLM_SILENCE_TIMEOUT_SECONDS


class VllmError(Exception):
    """vLLM answered with an HTTP error status instead of starting a reply."""


def parse_stream_line(line: str) -> dict | None:
    """Turn one 'data: {...}' line from vLLM into a dictionary; ignore anything else."""
    # A streamed reply is plain text lines. Blank lines separate pieces, and the
    # last line is the literal text "data: [DONE]", which carries no JSON.
    if not line.startswith("data: "):
        return None
    body = line[len("data: "):]
    if body == "[DONE]":
        return None
    return json.loads(body)


async def stream_chat(payload: dict) -> AsyncIterator[dict]:
    """Send the payload to vLLM and yield each reply piece as a dictionary, as it arrives.

    "async def" plus "yield" makes this an async generator: the caller loops over it with
    "async for" and gets each piece the moment it arrives, instead of waiting for all of them.
    """
    # Wait at most 10 seconds to connect, write, or get a connection from the pool,
    # but allow a long silence while vLLM reads the prompt or thinks.
    timeout = httpx.Timeout(10.0, read=VLLM_SILENCE_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # client.stream returns once the headers arrive; the body is read line by line below.
        async with client.stream("POST", VLLM_CHAT_URL, json=payload) as response:
            if response.status_code != 200:
                # aread loads the error body so the real reason (for example a rejected
                # field) reaches our logs and the database instead of a bare status.
                body = await response.aread()
                raise VllmError(f"vLLM replied HTTP {response.status_code}: {body[:500].decode(errors='replace')}")
            async for line in response.aiter_lines():
                piece = parse_stream_line(line)
                if piece is not None:
                    yield piece
