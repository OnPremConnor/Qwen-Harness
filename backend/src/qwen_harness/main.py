"""Create the FastAPI app and attach its route groups."""

import logging

from fastapi import FastAPI

from qwen_harness.routes.chat import router as chat_router
from qwen_harness.routes.page import router as page_router

# Uvicorn sets up only its own loggers. Python's default level is WARNING and nothing prints our
# INFO lines, so without this call they are dropped. basicConfig sends INFO and above to the terminal.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI()

# Each include_router call adds the URLs defined in that route file to the app.
app.include_router(page_router)
app.include_router(chat_router)
