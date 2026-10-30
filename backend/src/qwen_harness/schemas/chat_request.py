"""The JSON shape the browser sends to POST /chat."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    # FastAPI uses this field name to read {"message": "..."} from the browser.
    message: str
