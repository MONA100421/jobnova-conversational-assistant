# app/job_api.py
# Mock Jobnova API implementation: load jobs, score, and return reasons.

import json
from pathlib import Path
from typing import List
from .schemas import JobPreference, MatchItem
from .utils import normalize_text


_DATA = json.loads(Path("data/mock_jobs.json").read_text(encoding="utf-8"))


def _skill_overlap(a: List[str], b: List[str]) -> List[str]:
    aset = {normalize_text(x) for x in a if x}
    bset = {normalize_text(x) for x in b if x}
    return sorted(list(aset & bset))


def score_job(pref: JobPreference, job: dict) -> float:
    """Very simple heuristic scorer; deterministic and explainable."""
    s = 0.0
    if pref.role and pref.role.lower() in job["title"].lower():
        s += 2.0
    if pref.location and pref.location.lower() in job["location"].lower():
        s += 1.4
    if pref.domain and pref.domain.lower() == str(job.get("domain", "")).lower():
        s += 1.1
    if pref.employment_type and pref.employment_type == job.get("employment_type"):
        s += 0.9
    if pref.remote is not None and pref.remote == job.get("remote"):
        s += 0.8
    if pref.seniority and pref.seniority == job.get("seniority"):
        s += 0.6
    if pref.skills:
        s += min(len(_skill_overlap(pref.skills, job.get("skills", []))), 6) * 0.55
    # Coarse salary gate: prefer jobs meeting minimum
    if pref.salary_min and job.get("salary_min"):
        if job["salary_min"] >= pref.salary_min:
            s += 0.7
        else:
            s -= 0.5
    return s


def reasons(pref: JobPreference, job: dict) -> List[str]:
    r = []
    if pref.role and pref.role.lower() in job["title"].lower():
        r.append("Title matches desired role")
    if pref.location and pref.location.lower() in job["location"].lower():
        r.append("Preferred location matched")
    if pref.domain and pref.domain and pref.domain.lower() == str(job.get("domain", "")).lower():
        r.append("Domain aligned")
    if pref.remote is not None and pref.remote == job.get("remote"):
        r.append("Remote preference matched")
    ov = _skill_overlap(pref.skills or [], job.get("skills", []))
    if ov:
        r.append(f"Skill overlap: {', '.join(ov)}")
    if pref.salary_min and job.get("salary_min") and job["salary_min"] >= pref.salary_min:
        r.append("Salary meets minimum requirement")
    if pref.employment_type and pref.employment_type == job.get("employment_type"):
        r.append("Employment type aligned")
    return r


def query_top_n(pref: JobPreference, n: int = 10) -> List[MatchItem]:
    scored: List[MatchItem] = []
    for job in _DATA:
        sc = score_job(pref, job)
        if sc <= 0:
            continue
        sr = job.get("salary_min"), job.get("salary_max"), job.get("salary_unit", "year")
        item = MatchItem(
            job_id=job["job_id"],
            title=job["title"],
            company=job["company"],
            location=job["location"],
            salary_range=f"{sr[0]}–{sr[1]} / {sr[2]}" if sr[0] and sr[1] else None,
            domain=job.get("domain"),
            reasons=reasons(pref, job),
            score=round(sc, 3),
        )
        scored.append(item)
    return sorted(scored, key=lambda x: x.score, reverse=True)[:n]
