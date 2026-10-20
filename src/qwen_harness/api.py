from fastapi import FastAPI
from pydantic import BaseModel

from qwen_harness.vllm_client import send_request


class ChatRequest(BaseModel):
    """The JSON body our /chat caller sends, before we build a vLLM request."""

    # "message" is our API's required field; FastAPI checks that it is text.
    message: str


# Uvicorn loads this object from qwen_harness.api:app to serve our routes.
app = FastAPI()


# FastAPI parses and validates the caller's JSON before calling chat().
@app.post("/chat")
def chat(chat_request: ChatRequest) -> dict:
    # chat_request is a ChatRequest object; .message is the caller's text.
    # vLLM is a separate server and requires its own model/messages body.
    vllm_request_body = {
        "model": "qwen3.8-27b-fp8",
        "messages": [
            # Only this turn is sent; this route does not keep chat history yet.
            {"role": "user", "content": chat_request.message},
        ],
    }

    # This starts a second HTTP POST, from our API to vLLM.
    vllm_response = send_request(vllm_request_body)
    # .json() parses vLLM's reply body into Python data; FastAPI sends it to our caller.
    return vllm_response.json()
