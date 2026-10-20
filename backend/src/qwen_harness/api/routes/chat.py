"""Receive chat requests from Postman or a future dashboard."""

from fastapi import APIRouter

from qwen_harness.api.schemas.chat import ChatRequest
from qwen_harness.harness.chat import generate_chat_completion

router = APIRouter()


@router.post("/chat")
def chat(chat_request: ChatRequest) -> dict:
    # FastAPI has checked the incoming JSON against ChatRequest by this point.
    return generate_chat_completion(chat_request.message)
