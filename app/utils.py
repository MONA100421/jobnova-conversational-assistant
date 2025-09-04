# app/utils.py
# Normalization and parsing helpers.

import re
from typing import Optional, Tuple


_LOC_ALIASES = {
    "sf": "san francisco",
    "bay area": "bay area",
    "silicon valley": "bay area",
    "la": "los angeles",
    "nyc": "new york",
}

_EMPLOYMENT_TYPES = {"full-time", "part-time", "intern", "contract", "temporary"}


def normalize_text(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return re.sub(r"\s+", " ", s.strip().lower())


def normalize_location(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    s = normalize_text(s)
    return _LOC_ALIASES.get(s, s)


def normalize_employment_type(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    s = normalize_text(s)
    # common variants
    if s in _EMPLOYMENT_TYPES:
        return s
    if s in {"full time", "ft"}:
        return "full-time"
    if s in {"part time", "pt"}:
        return "part-time"
    if s in {"internship"}:
        return "intern"
    return s


def parse_salary_span(text: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Parse salary expressions like:
      - "$120k-$160k", "120k–160k", "30-45/hr", "$35/hour", "110000/yr"
    Returns (min, max, unit) where unit ∈ {"year", "hour"} or None.
    Numbers are normalized to integers (k -> *1000).
    """
    if not text:
        return None, None, None
    t = text.lower().replace(",", "")
    unit = None
    if "/hr" in t or "/hour" in t or "hour" in t or "hr" in t:
        unit = "hour"
    if "/yr" in t or "/year" in t or "year" in t or "annum" in t or "annual" in t:
        unit = "year" if unit is None else unit

    # capture two numbers
    nums = re.findall(r"\$?\s*([0-9]+\.?[0-9]*)(k)?", t)
    values = []
    for n, kflag in nums:
        val = float(n)
        if kflag == "k":
            val *= 1000
        values.append(int(round(val)))
    if not values:
        return None, None, unit
    if len(values) == 1:
        return values[0], None, unit
    # choose first two numeric spans
    return min(values[0], values[1]), max(values[0], values[1]), unit
