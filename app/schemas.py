# app/schemas.py
# Pydantic models for request/response contracts.

from pydantic import BaseModel, Field
from typing import List, Optional


class JobPreference(BaseModel):
    """Structured job intent extracted from user utterances."""
    role: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None  # unified to integer (hourly or yearly -> keep raw in notes if unknown)
    salary_max: Optional[int] = None
    salary_unit: Optional[str] = None  # "year" | "hour" | None
    employment_type: Optional[str] = None  # "full-time" | "part-time" | "intern"
    domain: Optional[str] = None  # e.g., "startup", "fintech", "healthcare"
    seniority: Optional[str] = None  # "intern" | "junior" | "mid" | "senior" | ...
    remote: Optional[bool] = None
    skills: List[str] = Field(default_factory=list)
    notes: Optional[str] = None  # original text / disambiguation crumbs


class ChatTurn(BaseModel):
    """Single chat turn coming from the UI/client."""
    session_id: str
    user_utterance: str


class ClarifyQuestion(BaseModel):
    """A single follow-up question for a missing or ambiguous field."""
    field: str
    question: str


class MatchItem(BaseModel):
    """One matched job item returned to the client."""
    job_id: str
    title: str
    company: str
    location: str
    salary_range: Optional[str] = None  # human-readable like "120k–160k / year" or "30–45 / hour"
    domain: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    score: float


class ChatResponse(BaseModel):
    """Assistant response for a chat turn including suggestions and results."""
    assistant_reply: str
    asked_clarifications: List[ClarifyQuestion] = Field(default_factory=list)
    parsed_preferences: JobPreference
    top_matches: List[MatchItem] = Field(default_factory=list)
