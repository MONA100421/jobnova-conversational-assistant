# app/orchestrator.py
# Dialogue orchestration: parse -> merge session -> clarify -> query -> format reply. ENGLISH ONLY.

from typing import List
from .schemas import ChatResponse, ChatTurn, JobPreference, ClarifyQuestion, MatchItem
from .memory import InMemorySession
from .llm import parse_intent, gen_clarify_questions
from .job_api import query_top_n

_mem = InMemorySession()


def _format_top3_preview(matches: List[MatchItem]) -> str:
    """Compose a short preview listing the top 3 matches with reasons."""
    if not matches:
        return "No matching jobs found yet."
    msg = f"I found {len(matches)} option(s). Here are the top {min(3, len(matches))}:\n"
    for i, m in enumerate(matches[:3], 1):
        rs = "; ".join(m.reasons or [])
        msg += f"{i}. {m.title} @ {m.company} ({m.location}) — {rs}\n"
    return msg.strip()


def handle_chat(turn: ChatTurn) -> ChatResponse:
    # 1) Parse user utterance into a structured preference
    parsed: JobPreference = parse_intent(turn.user_utterance)

    # 2) Merge into session memory
    pref: JobPreference = _mem.update_preferences(turn.session_id, parsed.model_dump())

    # 3) Check for missing/ambiguous critical fields -> ask follow-ups
    missing = gen_clarify_questions(pref)
    if missing:
        qs = [ClarifyQuestion(field=k, question=v) for k, v in missing.items()]
        reply = "To improve match quality, please clarify:\n- " + "\n- ".join(
            [q.question for q in qs][:3]
        )
        return ChatResponse(
            assistant_reply=reply,
            asked_clarifications=qs,
            parsed_preferences=pref,
            top_matches=[],
        )

    # 4) Query mock Jobnova API for top N matches
    matches: List[MatchItem] = query_top_n(pref, n=10)

    # 5) Fallback messages
    if not matches:
        msg = (
            "No roles match your current filters. Consider broadening location, "
            "title, or compensation range and try again."
        )
    else:
        msg = _format_top3_preview(matches)

    return ChatResponse(
        assistant_reply=msg,
        asked_clarifications=[],
        parsed_preferences=pref,
        top_matches=matches,
    )
