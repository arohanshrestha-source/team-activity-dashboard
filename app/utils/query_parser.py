import re
from typing import Dict, List, Optional, Tuple

# TODO: add your real people here
# Keys are lowercase names you expect in questions (e.g., "john", "sarah", "arohan")
USER_DIRECTORY: Dict[str, Dict[str, str]] = {

    "arohan": {"aliases": ["arohan", "arohan shrestha"],"jira": "arohanshrestha@utexas.edu", "github": "octocat"},
    "sarah": {"aliases": ["sarah"], "jira": "...", "github": "arohanshrestha-source"},
    "mike": {"aliases": ["mike", "mike smith"],"jira": "mike.smith@company.com","github": "octocat"}, 
    "alex": {"aliases": ["alex", "alex johnson"],"jira": "alex.johnson@company.com","github": "octocat"},

   
}

# JIRA issue key pattern: PROJECT-NUMBER (e.g. SAM1-8, KAN-2, PROJ-123)
JIRA_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b", re.IGNORECASE)


def extract_jira_issue_key(question: str) -> Optional[str]:
    """
    Find a JIRA issue key (e.g. SAM1-8, KAN-2) in the question.
    Returns the first match, normalized to uppercase for the key part.
    """
    m = JIRA_KEY_PATTERN.search(question.strip())
    if not m:
        return None
    key = m.group(1)
    # Normalize: PROJ-123 stays, sam1-8 -> SAM1-8
    parts = key.upper().rsplit("-", 1)
    return f"{parts[0]}-{parts[1]}" if len(parts) == 2 else key.upper()


# GitHub PR: URL (github.com/owner/repo/pull/123) or owner/repo#123 or "PR #5 in owner/repo"
GITHUB_PR_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(\d+)",
    re.IGNORECASE,
)
GITHUB_PR_REPO_HASH = re.compile(r"\b([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)#(\d+)\b")
GITHUB_PR_NUM_IN_REPO = re.compile(
    r"(?:PR|pull\s+request)\s*#?\s*(\d+)\s+(?:in\s+)?([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)",
    re.IGNORECASE,
)
GITHUB_PR_REPO_NUM = re.compile(
    r"\b([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)\s+(?:PR|pull\s+request)\s*#?\s*(\d+)\b",
    re.IGNORECASE,
)


def extract_github_pr_ref(question: str) -> Optional[Tuple[str, str, int]]:
    """
    Find a GitHub PR reference in the question.
    Returns (owner, repo, pr_number) or None.
    Supports: github.com/owner/repo/pull/123, owner/repo#123, PR #5 in owner/repo, owner/repo PR 5.
    """
    q = question.strip()
    # URL first
    m = GITHUB_PR_URL.search(q)
    if m:
        return (m.group(1), m.group(2), int(m.group(3)))
    m = GITHUB_PR_REPO_HASH.search(q)
    if m:
        return (m.group(1), m.group(2), int(m.group(3)))
    m = GITHUB_PR_NUM_IN_REPO.search(q)
    if m:
        return (m.group(2), m.group(3), int(m.group(1)))
    m = GITHUB_PR_REPO_NUM.search(q)
    if m:
        return (m.group(1), m.group(2), int(m.group(3)))
    return None


def extract_person_key(question: str) -> Optional[str]:
    """
    Find a known person key (from USER_DIRECTORY) mentioned in the question.
    Returns the first match.
    """
    keys = extract_person_keys(question)
    return keys[0] if keys else None


# Phrases that mean "return everyone in the directory"
ALL_USERS_PHRASES = [
    r"\ball\s+(?:the\s+)?users?\b",
    r"\ball\s+(?:the\s+)?people\b",
    r"\ball\s+(?:team\s+)?members?\b",
    r"\beveryone\b",
    r"\beverybody\b",
    r"\beveryone'?s?\b",
    r"\beverybody'?s?\b",
    # "The team" / team activities / casual phrasings
    r"\bthe\s+team\b",
    r"\bteam\s+doing\b",
    r"\bteam\s+activit",
    r"\bwhat(?:'s|s|\s+is)\s+the\s+team\b",
    r"\bwhat\s+the\s+team\b",
    r"\bteam\s*,?\s*what\b",
    r"\bwhat\s+they\s+doin",
    r"\bhow'?s\s+the\s+team\b",
    r"\bteam\s+work\b",
    r"\bteam\s+status\b",
    r"\bteam\s+up\s+to\b",
    r"\bwhat'?s\s+the\s+team\b",
]


def extract_person_keys(question: str) -> List[str]:
    """
    Find all known person keys mentioned in the question.
    Returns in order of first appearance in the question.
    If the question asks for "all users" / "everyone", returns all keys.
    """
    q = question.lower()
    # Check for "all users", "everyone", etc.
    for pat in ALL_USERS_PHRASES:
        if re.search(pat, q):
            return list(USER_DIRECTORY.keys())

    found_with_pos: List[Tuple[int, str]] = []
    for name in USER_DIRECTORY.keys():
        m = re.search(rf"\b{re.escape(name)}\b", q)
        if m:
            found_with_pos.append((m.start(), name))
    found_with_pos.sort(key=lambda x: x[0])
    return [name for _, name in found_with_pos]

def get_accounts(person_key: str) -> Dict[str, str]:
    return USER_DIRECTORY.get(person_key, {})


def get_default_person() -> Optional[str]:
    """Return first person in directory when no one is specified."""
    if not USER_DIRECTORY:
        return None
    return next(iter(USER_DIRECTORY.keys()))


def extract_mentioned_unknown_person(question: str) -> Optional[str]:
    """
    Detect if the user mentioned a specific person we don't have in USER_DIRECTORY.
    E.g. "what is Jerry working on" when Jerry isn't in the directory.
    Returns the mentioned name if found and unknown, else None.
    """
    q = question.strip()
    q_lower = q.lower()

    # Patterns where a name typically appears (capture group = potential name)
    patterns = [
        r"what\s+is\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+working\s+on",
        r"what'?s\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+working\s+on",
        r"what\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+is\s+up\s+to",
        r"what\s+is\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+up\s+to",  # "what is jerry up to"
        r"what'?s\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+up\s+to",
        r"(?:give|show|tell)\s+(?:me\s+)?what\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+is\s+up\s+to",
        r"how\s+is\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+doing",
        r"what\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+is\s+doing",
        r"what'?s\s+([a-zA-Z][a-zA-Z\s\-]*?)\s+doing",
        r"([a-zA-Z][a-zA-Z\s\-]*?)'?s\s+activit",
        r"activit(?:y|ies)\s+(?:for|of)\s+([a-zA-Z][a-zA-Z\s\-]+?)(?:\s+and|\s*$|\?)",
        r"show\s+(?:me\s+)?([a-zA-Z][a-zA-Z\s\-]*?)(?:'?s)?\s+(?:github|jira|activit)",
        r"(?:get|fetch)\s+([a-zA-Z][a-zA-Z\s\-]*?)(?:'?s)?\s+(?:github|jira|activit)",
        r"(?:get|fetch)\s+([a-zA-Z][a-zA-Z\s\-]+?)\s+and\s+",  # "get Bob and Jane"
    ]

    for pat in patterns:
        m = re.search(pat, q_lower, re.IGNORECASE)
        if m:
            # Use original question for capture to preserve casing (e.g. "Jerry")
            m_orig = re.search(pat, q, re.IGNORECASE)
            name = (m_orig.group(1) if m_orig else m.group(1)).strip()
            if len(name) < 2:
                continue
            # Normalize: "jerry smith" -> check "jerry" and "jerry smith" etc.
            name_lower = name.lower()
            # "everyone" / "everybody" are handled by extract_person_keys, not unknown
            if name_lower in ("everyone", "everybody", "all"):
                return None
            # Is this person in our directory? (check by key or alias)
            for key in USER_DIRECTORY.keys():
                if key in name_lower or name_lower in key:
                    return None  # Known person
                aliases = USER_DIRECTORY[key].get("aliases", [])
                if any(a.lower() in name_lower or name_lower in a.lower() for a in aliases):
                    return None  # Known person
            # Not found - they mentioned someone we don't have
            return name.strip()

    return None
