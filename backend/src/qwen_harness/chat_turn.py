"""Run one chat turn: read saved history, stream the reply from vLLM, save what happened."""

import asyncio
import logging
import time
from contextlib import aclosing
from datetime import datetime, timezone
from uuid import uuid4

from qwen_harness.messages import load_history, save_turn
from qwen_harness.model_requests import save_model_request
from qwen_harness.settings import VLLM_MODEL
from qwen_harness.vllm_client import stream_chat

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


async def run_turn(message: str, conversation_id: str | None, reasoning_effort: str):
    """Yield one event dictionary at a time for the browser, then always record the outcome.

    The SQLite calls in here are ordinary blocking code. Each takes a few milliseconds,
    so they briefly pause this one-user server; that is fine for a local baseline.
    """
    # A new chat has no ID yet, so make one. "or" picks the right side when the left is None.
    conversation_id = conversation_id or uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    clock_start = time.monotonic()

    def seconds_so_far() -> float:
        return round(time.monotonic() - clock_start, 3)

    messages = build_messages(load_history(conversation_id), message)
    # This new dictionary is the JSON body vLLM receives. stream=True asks for the reply
    # in pieces; include_usage adds a last piece that counts the tokens.
    payload = {
        "model": VLLM_MODEL,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "reasoning_effort": reasoning_effort,
    }
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
        # aclosing makes sure the connection to vLLM is closed even if we stop early.
        async with aclosing(stream_chat(payload)) as pieces:
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
                        yield {"type": "reasoning", "text": thinking}
                    if answer:
                        if seconds_to_answer is None:
                            seconds_to_answer = seconds_so_far()
                        answer_parts.append(answer)
                        yield {"type": "answer", "text": answer}
                    finish_reason = choice.get("finish_reason") or finish_reason
        answer_text = "".join(answer_parts).strip()
        if not answer_text:
            raise NoAnswerText(f"finish_reason={finish_reason}")
        user_id, assistant_id = save_turn(conversation_id, message, answer_text)
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
        # Runs after success, failure, and Stop alike, so every request leaves one row.
        details = usage.get("completion_tokens_details") or {}
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
            "reasoning_tokens": details.get("reasoning_tokens"),
            "finish_reason": finish_reason,
            "seconds_to_first_token": seconds_to_first_token,
            "seconds_to_answer": seconds_to_answer,
            "seconds_total": seconds_total,
            "reasoning_text": "".join(thinking_parts) or None,
            "user_message_id": user_id,
            "assistant_message_id": assistant_id,
        }
        try:
            save_model_request(record)
        except Exception:
            # This row is bookkeeping. If it cannot be written (for example the database
            # is locked), log why, but still deliver the reply or the real error below.
            logger.exception("could not save the model_requests row for conversation=%s", conversation_id)
        logger.info(
            "chat %s conversation=%s seconds=%s first_token=%s prompt_tokens=%s "
            "completion_tokens=%s reasoning_tokens=%s finish=%s",
            status, conversation_id, seconds_total, seconds_to_first_token,
            usage.get("prompt_tokens"), usage.get("completion_tokens"),
            details.get("reasoning_tokens"), finish_reason,
        )

    # A Stop re-raised above, so this point is reached only after success or a handled error.
    if status == "error":
        yield {"type": "error", "conversation_id": conversation_id, "message": error_text}
        return
    # Speed of the writing phase only: tokens divided by the time after the first piece.
    writing_seconds = seconds_total - (seconds_to_first_token or 0)
    completion_tokens = usage.get("completion_tokens")
    tokens_per_second = (
        round(completion_tokens / writing_seconds, 1) if completion_tokens and writing_seconds > 0 else None
    )
    yield {
        "type": "done",
        "conversation_id": conversation_id,
        "user_message_id": user_id,
        "assistant_message_id": assistant_id,
        "finish_reason": finish_reason,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": completion_tokens,
        "reasoning_tokens": details.get("reasoning_tokens"),
        "seconds_to_first_token": seconds_to_first_token,
        "seconds_total": seconds_total,
        "tokens_per_second": tokens_per_second,
    }
