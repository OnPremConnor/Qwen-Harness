"""Create the FastAPI application and attach its routes."""

from fastapi import FastAPI

from qwen_harness.api.routes import chat

app = FastAPI()
app.include_router(chat.router)
