"""Create the FastAPI app and attach its route groups."""

from fastapi import FastAPI

from qwen_harness.routes.chat import router as chat_router
from qwen_harness.routes.page import router as page_router

app = FastAPI()

# Each include_router call adds the URLs defined in that route file to the app.
app.include_router(page_router)
app.include_router(chat_router)
