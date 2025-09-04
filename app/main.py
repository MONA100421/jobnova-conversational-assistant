# app/main.py
# FastAPI entrypoint with health, mock API, and chat API routes.

from fastapi import FastAPI
from .schemas import ChatTurn, JobPreference
from .orchestrator import handle_chat
from .job_api import query_top_n

app = FastAPI(title="JobNova Conversational Assistant", version="1.0.0")


@app.get("/health")
def health():
    return {"ok": True}


# Mock Jobnova API endpoint (for grading/demo)
@app.post("/mock/jobs")
def mock_jobs(pref: JobPreference):
    return [m.model_dump() for m in query_top_n(pref)]


# Main conversational endpoint
@app.post("/chat")
def chat(turn: ChatTurn):
    return handle_chat(turn)
