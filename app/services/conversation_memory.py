"""
Conversation memory for follow-up context.
Stores last question, intent, person_keys (for activity follow-ups)
and conversation_history (for general chat follow-ups).
Uses Redis when REDIS_URL is set; otherwise in-memory.
"""
import json
import time
from typing import Any, Dict, List, Optional

from app.services.redis_client import get_redis

# session_id -> { last_question, last_intent, last_person_keys, conversation_history, updated_at }
_store: Dict[str, Dict[str, Any]] = {}
# Max conversation turns to keep (user + assistant = 2 messages per turn)
_MAX_HISTORY_TURNS = 10
# TTL: 30 minutes
_TTL_SEC = 30 * 60
# Max sessions to keep (LRU eviction) for in-memory fallback
_MAX_SESSIONS = 1000
_PREFIX = "session:"


def _evict_expired():
    """Remove expired sessions (in-memory only)."""
    now = time.time()
    expired = [s for s, v in _store.items() if (now - v.get("updated_at", 0)) > _TTL_SEC]
    for s in expired:
        _store.pop(s, None)


def _evict_if_needed():
    """Evict oldest if over limit (in-memory only)."""
    if len(_store) <= _MAX_SESSIONS:
        return
    sorted_keys = sorted(_store.keys(), key=lambda k: _store[k].get("updated_at", 0))
    for k in sorted_keys[: len(sorted_keys) - _MAX_SESSIONS]:
        _store.pop(k, None)


def set_context(
    session_id: str,
    question: str,
    intent: str,
    person_keys: list,
) -> None:
    """Store conversation context for activity follow-ups."""
    r = get_redis()
    if r:
        try:
            key = _PREFIX + session_id
            raw = r.get(key)
            existing = json.loads(raw) if raw else {}
            ctx = {
                "last_question": question,
                "last_intent": intent,
                "last_person_keys": person_keys,
                "conversation_history": existing.get("conversation_history", []),
                "updated_at": time.time(),
            }
            r.setex(key, _TTL_SEC, json.dumps(ctx))
        except Exception:
            pass
        return
    _evict_expired()
    _evict_if_needed()
    existing = _store.get(session_id) or {}
    _store[session_id] = {
        "last_question": question,
        "last_intent": intent,
        "last_person_keys": person_keys,
        "conversation_history": existing.get("conversation_history", []),
        "updated_at": time.time(),
    }


def append_exchange(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """Append a user/assistant exchange to conversation history (for general chat)."""
    r = get_redis()
    if r:
        try:
            key = _PREFIX + session_id
            raw = r.get(key)
            entry = json.loads(raw) if raw else {}
            history = entry.get("conversation_history", [])
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_msg})
            if len(history) > _MAX_HISTORY_TURNS * 2:
                history = history[-(_MAX_HISTORY_TURNS * 2) :]
            entry["conversation_history"] = history
            entry["updated_at"] = time.time()
            r.setex(key, _TTL_SEC, json.dumps(entry))
        except Exception:
            pass
        return
    _evict_expired()
    _evict_if_needed()
    entry = _store.get(session_id) or {}
    history = entry.get("conversation_history", [])
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})
    if len(history) > _MAX_HISTORY_TURNS * 2:
        history = history[-(_MAX_HISTORY_TURNS * 2) :]
    _store[session_id] = {**entry, "conversation_history": history, "updated_at": time.time()}


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history for general chat (list of {role, content})."""
    r = get_redis()
    if r:
        try:
            key = _PREFIX + session_id
            raw = r.get(key)
            if not raw:
                return []
            ctx = json.loads(raw)
            return ctx.get("conversation_history", [])
        except Exception:
            return []
    _evict_expired()
    ctx = _store.get(session_id)
    if not ctx:
        return []
    if (time.time() - ctx.get("updated_at", 0)) > _TTL_SEC:
        _store.pop(session_id, None)
        return []
    return ctx.get("conversation_history", [])


def get_context(session_id: str) -> Optional[Dict[str, Any]]:
    """Get stored context for a session."""
    r = get_redis()
    if r:
        try:
            key = _PREFIX + session_id
            raw = r.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception:
            return None
    _evict_expired()
    ctx = _store.get(session_id)
    if not ctx:
        return None
    if (time.time() - ctx.get("updated_at", 0)) > _TTL_SEC:
        _store.pop(session_id, None)
        return None
    return ctx
