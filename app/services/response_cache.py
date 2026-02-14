"""
Simple TTL cache for expensive responses (JIRA, GitHub, AI).
Reduces repeated fetches for the same or similar questions.
Uses Redis when REDIS_URL is set; otherwise in-memory.
"""
import hashlib
import json
import time
from typing import Any, Dict, Optional

from app.services.redis_client import get_redis

_store: Dict[str, Dict[str, Any]] = {}
# TTL: 5 minutes (activity data can change)
_TTL_SEC = 5 * 60
# Max cache entries (evict oldest) for in-memory fallback
_MAX_ENTRIES = 500
_PREFIX = "rc:"


def _make_key(intent: str, person_keys: list, question: str) -> str:
    """Generate cache key from intent, person_keys, and normalized question."""
    normalized = " ".join(question.lower().strip().split())
    parts = [intent, json.dumps(sorted(person_keys)), normalized]
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return h


def _evict_expired():
    """Remove expired entries (in-memory only)."""
    now = time.time()
    expired = [k for k, v in _store.items() if (now - v.get("cached_at", 0)) > _TTL_SEC]
    for k in expired:
        _store.pop(k, None)


def _evict_if_needed():
    """Evict oldest entries if over limit (in-memory only)."""
    if len(_store) <= _MAX_ENTRIES:
        return
    sorted_keys = sorted(_store.keys(), key=lambda k: _store[k].get("cached_at", 0))
    for k in sorted_keys[: len(sorted_keys) - _MAX_ENTRIES]:
        _store.pop(k, None)


def get(intent: str, person_keys: list, question: str) -> Optional[Dict[str, Any]]:
    """
    Get cached response if present and not expired.
    Returns dict with answer_md, links, etc. or None.
    """
    r = get_redis()
    if r:
        try:
            key = _PREFIX + _make_key(intent, person_keys, question)
            raw = r.get(key)
            if not raw:
                return None
            entry = json.loads(raw)
            return entry.get("value")
        except Exception:
            return None
    _evict_expired()
    key = _make_key(intent, person_keys, question)
    entry = _store.get(key)
    if not entry:
        return None
    if (time.time() - entry.get("cached_at", 0)) > _TTL_SEC:
        _store.pop(key, None)
        return None
    return entry.get("value")


def set(
    intent: str,
    person_keys: list,
    question: str,
    value: Dict[str, Any],
) -> None:
    """Store response in cache."""
    r = get_redis()
    if r:
        try:
            key = _PREFIX + _make_key(intent, person_keys, question)
            payload = json.dumps({"value": value, "cached_at": time.time()})
            r.setex(key, _TTL_SEC, payload)
        except Exception:
            pass
        return
    _evict_expired()
    _evict_if_needed()
    key = _make_key(intent, person_keys, question)
    _store[key] = {"value": value, "cached_at": time.time()}
