# app/llm.py
# Robust LLM wrapper with dotenv loading and offline fallback.

import json
import os
import re
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from importlib import resources

from .schemas import JobPreference
from .utils import (
    normalize_location,
    normalize_employment_type,
    parse_salary_span,
)

# Ensure environment variables from .env are loaded
load_dotenv()

# Create client (may be unused if we fall back)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _extract_json_block(text: str) -> Dict[str, Any]:
    """Extract the first JSON object found in the text; return {} on failure."""
    if not text:
        return {}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _load_prompt() -> str:
    """
    Read prompts/parse_intent.md using importlib.resources for robust packaging.
    Fallback to a minimal inline prompt if file is missing.
    """
    try:
        with resources.files("app").joinpath("../prompts/parse_intent.md").open("r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # Minimal inline prompt fallback
        return (
            'You are a job-intent parser. Return STRICT JSON with keys: '
            '{ "role": null, "location": null, "salary_min": null, "salary_max": null, '
            '"salary_unit": null, "employment_type": null, "domain": null, '
            '"seniority": null, "remote": null, "skills": [], "notes": null }. '
            'User: "{USER_UTTERANCE}"'
        )


def _fallback_parse_intent(utterance: str) -> JobPreference:
    """
    Offline heuristic when LLM is unavailable: naive extraction of a few fields.
    This guarantees /chat never crashes.
    """
    u = utterance.lower()
    role = None
    # crude role guess
    for kw in ["data analyst", "ai engineer", "ml engineer", "data scientist", "nlp engineer"]:
        if kw in u:
            role = kw.title()
            break

    # location guess
    location = None
    for loc in ["bay area", "san francisco", "los angeles", "new york", "austin", "remote"]:
        if loc in u:
            location = "Remote" if loc == "remote" else loc.title()
            break

    # salary
    smin, smax, sunit = parse_salary_span(utterance)

    # remote flag
    remote = True if "remote is fine" in u or "remote ok" in u or "remote" in u else None

    # skills (very rough)
    skills = []
    for sk in ["sql", "python", "tableau", "pandas", "langchain", "fastapi"]:
        if sk in u:
            skills.append(sk)

    return JobPreference(
        role=role,
        location=normalize_location(location),
        salary_min=smin,
        salary_max=smax,
        salary_unit=sunit,
        employment_type=None,
        domain=None,
        seniority=None,
        remote=remote,
        skills=skills,
        notes="parsed by offline fallback",
    )


def parse_intent(user_utterance: str) -> JobPreference:
    """
    Try the LLM first; if it fails for any reason (no key, network, bad model),
    fall back to a heuristic parser so /chat always returns a response.
    """
    prompt_template = _load_prompt()
    prompt = prompt_template.replace("{USER_UTTERANCE}", user_utterance)

    if client is None:
        return _fallback_parse_intent(user_utterance)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        txt = resp.choices[0].message.content or ""
        data = _extract_json_block(txt)

        # Normalize and return
        role = data.get("role")
        location = normalize_location(data.get("location"))
        employment_type = normalize_employment_type(data.get("employment_type"))
        salary_min = data.get("salary_min")
        salary_max = data.get("salary_max")
        salary_unit = data.get("salary_unit")
        notes = data.get("notes")

        # Infer salary unit from raw utterance if missing
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
    except OpenAIError:
        # Explicit API errors
        return _fallback_parse_intent(user_utterance)
    except Exception:
        # Any other unexpected issues (JSON, prompt, etc.)
        return _fallback_parse_intent(user_utterance)


# English-only follow-up prompts
CLARIFY_MAP = {
    "role": "What role are you targeting? (e.g., Data Analyst, AI Engineer)",
    "location": "Which location or time zone do you prefer? Is remote acceptable?",
    "salary_min": "What is your minimum acceptable compensation? (please specify yearly/hourly)",
    "employment_type": "Do you prefer full-time, part-time, intern, contract, or temporary?",
    "domain": "Any industry preference? (e.g., startup, fintech, healthcare)",
}


def gen_clarify_questions(pref: JobPreference) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for field, q in CLARIFY_MAP.items():
        if getattr(pref, field) in (None, "", []):
            out[field] = q
    return out
