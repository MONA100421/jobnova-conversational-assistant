# app/memory.py
# Minimal in-memory session store. Swap to Redis for production.

from typing import Dict, Any
from time import time
from .schemas import JobPreference


class InMemorySession:
    """A tiny session store with soft TTL to keep memory bounded in demos."""
    def __init__(self, ttl_seconds: int = 3600):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _ensure(self, session_id: str) -> Dict[str, Any]:
        now = time()
        s = self._store.get(session_id)
        if not s or now - s.get("last_seen", 0) > self._ttl:
            s = {"preferences": JobPreference().model_dump(), "last_seen": now}
            self._store[session_id] = s
        else:
            s["last_seen"] = now
        return s

    def get(self, session_id: str) -> Dict[str, Any]:
        return self._ensure(session_id)

    def update_preferences(self, session_id: str, updates: Dict[str, Any]) -> JobPreference:
        s = self._ensure(session_id)
        # Merge non-empty values only
        merged = {**s["preferences"]}
        for k, v in updates.items():
            if v not in (None, "", [], {}):
                merged[k] = v
        pref = JobPreference(**merged)
        s["preferences"] = pref.model_dump()
        self._store[session_id] = s
        return pref
