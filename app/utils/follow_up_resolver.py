"""
Detects follow-up questions and resolves them using conversation context.
Examples: "what about Mike?", "and Sarah?", "show me more", "same for everyone"
"""
import re
from typing import Optional, Tuple

from app.utils.query_parser import USER_DIRECTORY, extract_person_keys


# Phrases that indicate a follow-up (short, context-dependent)
FOLLOW_UP_PREFIXES = [
    r"^(?:what\s+about|and|also|same\s+for|how\s+about)\s+",
    r"^\+?\s*",  # "+ Mike" style
]

# Short follow-ups that mean "add person X" or "show more"
FOLLOW_UP_PATTERNS = [
    (r"^(?:what\s+about|and|also|same\s+for|how\s+about)\s+(.+)$", "add_person"),
    (r"^(?:more|details|elaborate|expand)$", "more_detail"),
    (r"^(?:same|ditto|same\s+thing)$", "same_as_before"),
]


def _looks_like_follow_up(question: str) -> bool:
    """Quick heuristic: short question or starts with follow-up phrase."""
    q = question.lower().strip()
    if len(q) < 4:
        return False
    # Short questions (< 6 words) often need context
    word_count = len(q.split())
    if word_count <= 5:
        for pat in FOLLOW_UP_PREFIXES:
            if re.search(pat, q):
                return True
        # "Mike", "Sarah and Alex" - just names
        if word_count <= 3 and any(
            re.search(rf"\b{re.escape(name)}\b", q) for name in USER_DIRECTORY
        ):
            return True
    return False


def resolve_follow_up(
    question: str,
    last_question: str,
    last_intent: str,
    last_person_keys: list,
) -> Tuple[Optional[str], Optional[list], bool]:
    """
    Resolve a follow-up question using previous context.
    Returns: (resolved_question, person_keys, was_resolved)
    - If not a follow-up: returns (None, None, False)
    - If follow-up: returns (resolved_question, person_keys, True)
    """
    q = question.strip()
    if not _looks_like_follow_up(q):
        return (None, None, False)

    q_lower = q.lower()

    # "what about Mike?", "and Sarah?", "same for Alex"
    for pat, kind in FOLLOW_UP_PATTERNS:
        m = re.match(pat, q_lower)
        if m:
            if kind == "add_person":
                # Extract the person(s) from the follow-up
                rest = m.group(1).strip()
                new_keys = extract_person_keys(rest)
                if new_keys:
                    # Merge: previous + new (deduped, preserve order)
                    merged = list(dict.fromkeys(last_person_keys + new_keys))
                    resolved = f"Activity for {', '.join(k.capitalize() for k in merged)}"
                    return (resolved, merged, True)
            elif kind == "more_detail":
                # "more", "details" - same question, maybe we'd fetch more data later
                resolved = "More details on previous activity"
                return (resolved, last_person_keys, True)
            elif kind == "same_as_before":
                return (last_question, last_person_keys, True)

    # Short question with just names: "Mike", "Sarah and Alex"
    new_keys = extract_person_keys(q)
    if new_keys and last_intent in ("team_activity", "github_only", "jira_only"):
        resolved = f"Activity for {', '.join(k.capitalize() for k in new_keys)}"
        return (resolved, new_keys, True)

    return (None, None, False)
