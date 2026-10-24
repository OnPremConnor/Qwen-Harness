"""Run one chat turn: read saved history, stream the reply from vLLM, save what happened.

This is the service layer. It decides what happens and in what order. The SQL lives in
repositories/ and the HTTP calls to vLLM live in clients/; this file only calls them.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import datetime, timezone
from uuid import uuid4

from qwen_harness.clients import vllm_client
from qwen_harness.repositories import message_repository, model_request_repository
from qwen_harness.schemas.chat_events import (
    AnswerEvent,
    ChatEvent,
    DoneEvent,
    ErrorEvent,
    ReasoningEvent,
)
from qwen_harness.settings import VLLM_MODEL

logger = logging.getLogger(__name__)


class NoAnswerText(Exception):
    """The stream ended with no answer text to save, for example when thinking used every token."""


def build_messages(saved_rows: list[tuple[str, str]], new_message: str) -> list[dict[str, str]]:
    """Reshape SQLite tuples into the message dictionaries vLLM expects, in order."""
    # [] creates a new Python list for this request; it does not alter saved rows.
    messages = []
    for role, content in saved_rows:
        # Unpack each two-string tuple, then append a new dictionary.
        messages.append({"role": role, "content": content})
    # The new user text has not been saved yet, but the model must see it.
    messages.append({"role": "user", "content": new_message})
    return messages


def build_payload(messages: list[dict[str, str]], reasoning_effort: str) -> dict:
    """Make the JSON body vLLM receives; this is a new dictionary, separate from the browser's."""
    return {
        "model": VLLM_MODEL,
        "messages": messages,
        # stream=True asks for the reply in pieces; include_usage adds a last piece that
        # counts the tokens.
        "stream": True,
        "stream_options": {"include_usage": True},
        "reasoning_effort": reasoning_effort,
    }


def reasoning_tokens_in(usage: dict) -> int | None:
    """Pull the thinking-token count out of vLLM's usage piece; None if vLLM did not send it."""
    details = usage.get("completion_tokens_details") or {}
    return details.get("reasoning_tokens")


def build_done_event(
    conversation_id: str,
    user_id: int,
    assistant_id: int,
    finish_reason: str | None,
    usage: dict,
    seconds_to_first_token: float | None,
    seconds_total: float,
) -> DoneEvent:
    """Make the final event for a good turn, including the writing speed in tokens per second."""
    completion_tokens = usage.get("completion_tokens")
    # Speed of the writing phase only: tokens divided by the time after the first piece.
    writing_seconds = seconds_total - (seconds_to_first_token or 0)
    tokens_per_second = (
        round(completion_tokens / writing_seconds, 1) if completion_tokens and writing_seconds > 0 else None
    )
    return DoneEvent(
        conversation_id=conversation_id,
        user_message_id=user_id,
        assistant_message_id=assistant_id,
        finish_reason=finish_reason,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=completion_tokens,
        reasoning_tokens=reasoning_tokens_in(usage),
        seconds_to_first_token=seconds_to_first_token,
        seconds_total=seconds_total,
        tokens_per_second=tokens_per_second,
    )


async def run_turn(
    message: str, conversation_id: str | None, reasoning_effort: str
) -> AsyncIterator[ChatEvent]:
    """Yield events for the browser one at a time, then always record the outcome.

    This is an "async generator": an async function that uses yield, so the caller gets each
    event the moment it is made instead of waiting for the whole reply. The steps, in order:

      1. choose the conversation ID and start the clock
      2. read the saved history and build the request for vLLM
      3. read the reply pieces as they arrive, yielding thinking and answer events
      4. after a good answer, save both messages
      5. in "finally" (after success, failure, or Stop): record one model_requests row and log it
      6. yield the last event: done, or error

    The SQLite calls in here are ordinary blocking code. Each takes a few milliseconds,
    so they briefly pause this one-user server; that is fine for a local baseline.
    """
    # 1. A new chat has no ID yet, so make one. "or" picks the right side when the left is None.
    conversation_id = conversation_id or uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    clock_start = time.monotonic()

    def seconds_so_far() -> float:
        return round(time.monotonic() - clock_start, 3)

    # 2. Read history, then put the new message last.
    messages = build_messages(message_repository.load_history(conversation_id), message)
    payload = build_payload(messages, reasoning_effort)
    prompt_chars = sum(len(item["content"]) for item in messages)
    logger.info(
        "chat start conversation=%s effort=%s history_rows=%d prompt_chars=%d",
        conversation_id, reasoning_effort, len(messages) - 1, prompt_chars,
    )

    thinking_parts, answer_parts = [], []
    seconds_to_first_token = seconds_to_answer = None
    finish_reason = None
    usage = {}
    user_id = assistant_id = None
    # Stay "error" until the whole reply arrives and is saved; only then switch to "ok".
    status, error_text = "error", None
    try:
        # 3. aclosing makes sure the connection to vLLM is closed even if we stop early.
        async with aclosing(vllm_client.stream_chat(payload)) as pieces:
            async for piece in pieces:
                # Only the last piece carries usage, and it has no "choices".
                usage = piece.get("usage") or usage
                for choice in piece.get("choices", []):
                    delta = choice["delta"]
                    # vLLM 0.28.0 puts thinking in delta["reasoning"] and the answer in delta["content"].
                    thinking = delta.get("reasoning")
                    answer = delta.get("content")
                    if (thinking or answer) and seconds_to_first_token is None:
                        seconds_to_first_token = seconds_so_far()
                    if thinking:
                        thinking_parts.append(thinking)
                        yield ReasoningEvent(text=thinking)
                    if answer:
                        if seconds_to_answer is None:
                            seconds_to_answer = seconds_so_far()
                        answer_parts.append(answer)
                        yield AnswerEvent(text=answer)
                    finish_reason = choice.get("finish_reason") or finish_reason
        # 4. The answer often starts with blank lines (the real recorded stream does), so strip it.
        answer_text = "".join(answer_parts).strip()
        if not answer_text:
            raise NoAnswerText(f"finish_reason={finish_reason}")
        user_id, assistant_id = message_repository.save_turn(conversation_id, message, answer_text)
        status = "ok"
    except (asyncio.CancelledError, GeneratorExit):
        # The browser disconnected (its Stop button). Record it, then let the stop continue.
        status = "stopped"
        raise
    except Exception as error:
        # One place records the real cause: the exception class plus its message.
        error_text = f"{type(error).__name__}: {error}"
        logger.exception("chat failed conversation=%s", conversation_id)
    finally:
        # 5. Runs after success, failure, and Stop alike, so every request leaves one row.
        seconds_total = seconds_so_far()
        record = {
            "conversation_id": conversation_id,
            "started_at": started_at,
            "status": status,
            "error": error_text,
            "model": VLLM_MODEL,
            "reasoning_effort": reasoning_effort,
            "prompt_chars": prompt_chars,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": reasoning_tokens_in(usage),
            "finish_reason": finish_reason,
            "seconds_to_first_token": seconds_to_first_token,
            "seconds_to_answer": seconds_to_answer,
            "seconds_total": seconds_total,
            "reasoning_text": "".join(thinking_parts) or None,
            "user_message_id": user_id,
            "assistant_message_id": assistant_id,
        }
        try:
            model_request_repository.save_model_request(record)
        except Exception:
            # This row is bookkeeping. If it cannot be written (for example the database
            # is locked), log why, but still deliver the reply or the real error below.
            logger.exception("could not save the model_requests row for conversation=%s", conversation_id)
        logger.info(
            "chat %s conversation=%s seconds=%s first_token=%s prompt_tokens=%s "
            "completion_tokens=%s reasoning_tokens=%s finish=%s",
            status, conversation_id, seconds_total, seconds_to_first_token,
            usage.get("prompt_tokens"), usage.get("completion_tokens"),
            reasoning_tokens_in(usage), finish_reason,
        )

    # 6. A Stop re-raised above, so this point is reached only after success or a handled error.
    if status == "error":
        yield ErrorEvent(conversation_id=conversation_id, message=error_text)
        return
    yield build_done_event(
        conversation_id, user_id, assistant_id, finish_reason, usage, seconds_to_first_token, seconds_total
    )
