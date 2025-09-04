# app/llm.py
# LLM wrappers: intent parsing and clarify question generation. ENGLISH ONLY.

import json
import os
import re
from typing import Dict, Any
from openai import OpenAI
from .schemas import JobPreference
from .utils import normalize_location, normalize_employment_type, parse_salary_span

# Read API key from env; the client can be mocked in unit tests.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _extract_json_block(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a text blob safely."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def parse_intent(user_utterance: str) -> JobPreference:
    """
    Call the LLM to parse job intent into the strict JSON schema.
    Post-process to normalize fields and fill derived values like salary units.
    """
    prompt = open("prompts/parse_intent.md", "r", encoding="utf-8").read().replace(
        "{USER_UTTERANCE}", user_utterance
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    txt = resp.choices[0].message.content or ""
    data = _extract_json_block(txt)

    # Defensive defaults and normalization
    role = data.get("role")
    location = normalize_location(data.get("location"))
    employment_type = normalize_employment_type(data.get("employment_type"))
    salary_min = data.get("salary_min")
    salary_max = data.get("salary_max")
    salary_unit = data.get("salary_unit")
    notes = data.get("notes")

    # Try to infer salary unit from the original utterance if missing
    if not salary_unit and (salary_min or salary_max):
        _, _, unit = parse_salary_span(user_utterance)
        salary_unit = unit

    return JobPreference(
        role=role,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_unit=salary_unit,
        employment_type=employment_type,
        domain=data.get("domain"),
        seniority=data.get("seniority"),
        remote=data.get("remote"),
        skills=data.get("skills") or [],
        notes=notes,
    )


# Field -> follow-up question mapping (ENGLISH ONLY)
CLARIFY_MAP = {
    "role": "What role are you targeting? (e.g., Data Analyst, AI Engineer)",
    "location": "Which location or time zone do you prefer? Is remote acceptable?",
    "salary_min": "What is your minimum acceptable compensation? (please specify yearly/hourly)",
    "employment_type": "Do you prefer full-time, part-time, intern, contract, or temporary?",
    "domain": "Any industry preference? (e.g., startup, fintech, healthcare)",
}


def gen_clarify_questions(pref: JobPreference) -> Dict[str, str]:
    """Return follow-ups for missing/ambiguous key fields."""
    out: Dict[str, str] = {}
    for field, q in CLARIFY_MAP.items():
        if getattr(pref, field) in (None, "", []):
            out[field] = q
    return out
