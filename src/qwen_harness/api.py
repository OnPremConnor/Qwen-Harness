from fastapi import FastAPI


# Uvicorn imports this module and uses this FastAPI app object to handle requests.
app = FastAPI()


# The decorator sets the HTTP path; "chat" is our chosen Python function name.
@app.post("/chat")
def chat(payload: dict) -> dict:
    # FastAPI parses the incoming JSON body and passes it into this parameter.
    # Echo it for now so the caller can see what reached our route.
    return payload
