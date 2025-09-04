# tests/test_orchestrator.py
# Smoke tests for the orchestrator with an LLM stub (no external calls).

import os
from typing import Dict, Any
import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")  # avoid SDK complaints

from app.schemas import ChatTurn, JobPreference
from app import orchestrator as orch  # import module to allow monkeypatching symbols


def _stub_parse_intent(_: str) -> JobPreference:
    """Return a fixed, reasonable preference for testing."""
    return JobPreference(
        role="Data Analyst",
        location="bay area",
        salary_min=30,
        salary_max=45,
        salary_unit="hour",
        employment_type="intern",
        domain="startup",
        seniority="intern",
        remote=True,
        skills=["sql", "python", "tableau"],
        notes=None,
    )


def test_handle_chat_with_stubbed_llm(monkeypatch: pytest.MonkeyPatch):
    # Arrange: stub the LLM parser so we avoid network calls
    monkeypatch.setattr("app.llm.parse_intent", _stub_parse_intent)

    turn = ChatTurn(
        session_id="t1",
        user_utterance="Looking for a Data Analyst role in the Bay Area at a startup, remote OK, $35/hr+",
    )

    # Act
    resp = orch.handle_chat(turn)

    # Assert
    assert resp.parsed_preferences is not None
    assert resp.parsed_preferences.role == "Data Analyst"
    # When critical fields are present, the orchestrator should return matches or a clear message
    assert isinstance(resp.assistant_reply, str) and len(resp.assistant_reply) > 0
    # It should either ask no clarifications or return an empty list
    assert isinstance(resp.asked_clarifications, list)


def test_handle_chat_requests_clarification(monkeypatch: pytest.MonkeyPatch):
    # Arrange: return a preference missing key fields to trigger clarifications
    def _stub_missing(_: str) -> JobPreference:
        return JobPreference(role=None, location=None, remote=None, skills=[])

    monkeypatch.setattr("app.llm.parse_intent", _stub_missing)

    turn = ChatTurn(session_id="t2", user_utterance="")

    # Act
    resp = orch.handle_chat(turn)

    # Assert
    assert resp.top_matches == []
    assert resp.asked_clarifications  # should not be empty
    assert "clarify" in resp.assistant_reply.lower()
