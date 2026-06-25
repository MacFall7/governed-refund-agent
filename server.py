"""FastAPI app. Serves the single-page UI and the /chat endpoint.

Run:  python server.py    ->  http://localhost:8000
"""
import os
import pathlib

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent import run_agent

load_dotenv()
HERE = pathlib.Path(__file__).parent
app = FastAPI(title="Governed Refund Agent")


class ChatIn(BaseModel):
    message: str
    history: list = []


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.post("/chat")
def chat(body: ChatIn):
    if not os.environ.get("OPENAI_API_KEY"):
        return {"reply": "Server is missing OPENAI_API_KEY — set it in .env.",
                "trace": [], "receipt": None, "error": "missing OPENAI_API_KEY"}
    try:
        return run_agent(body.message, body.history)
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        return {
            "reply": "Sorry — the agent hit an error and stopped before deciding.",
            "trace": [{"type": "error", "detail": detail}],
            "receipt": None,
            "error": detail,
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
