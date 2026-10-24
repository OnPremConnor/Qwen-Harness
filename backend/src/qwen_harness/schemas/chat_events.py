"""The four kinds of event POST /chat streams to the browser, one JSON line each."""

from typing import Literal

from pydantic import BaseModel


class ReasoningEvent(BaseModel):
    """A piece of the model's thinking."""

    type: Literal["reasoning"] = "reasoning"
    text: str


class AnswerEvent(BaseModel):
    """A piece of the model's answer."""

    type: Literal["answer"] = "answer"
    text: str


class DoneEvent(BaseModel):
    """The turn finished and was saved. Carries the row IDs and the numbers for the stats line."""

    type: Literal["done"] = "done"
    conversation_id: str
    user_message_id: int
    assistant_message_id: int
    # "| None" means the value may be missing (JSON null), for example when vLLM sends no usage.
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    seconds_to_first_token: float | None
    seconds_total: float
    tokens_per_second: float | None


class ErrorEvent(BaseModel):
    """The turn failed. Nothing was saved to the chat; model_requests has the details."""

    type: Literal["error"] = "error"
    conversation_id: str
    message: str


# Any one of the four. This is the type of everything run_turn yields.
ChatEvent = ReasoningEvent | AnswerEvent | DoneEvent | ErrorEvent
