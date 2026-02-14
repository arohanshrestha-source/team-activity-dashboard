import json
from typing import Any, List, Optional

from app.config import get_settings


def _get_client():
    """
    Lazy-load OpenAI client so the app still runs
    even if AI is disabled or misconfigured.
    """
    from openai import OpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    return OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """You are an AI team activity assistant.

CRITICAL RULES:
- Use ONLY the provided data. Do NOT invent tickets, repos, commits, or PRs.
- Output MUST be VALID MARKDOWN ONLY.
- For a SINGLE person: use headings # Summary, ## JIRA, ## GitHub, ### Open Pull Requests, ### Commits, ### Recent Repositories.
- For MULTIPLE people: use # Summary, then for each person use ## PERSON_NAME with ### JIRA and ### GitHub subsections.
- Use '-' for bullets.
- INCLUDE clickable markdown links for JIRA tickets and GitHub PRs using [text](url) format.
- If a section has no items, include exactly one bullet explaining that.

CONTENT RULES:
- Summary: 1–2 concise sentences covering all people.
- JIRA: up to 5 issues per person, format: [KEY](url) — SUMMARY (STATUS)
- Open Pull Requests: up to 5 PRs per person, format: [TITLE](url) (REPO)
- Commits: up to 5 per person, format: [MESSAGE](url) (REPO)
- Recent Repositories: up to 5 repo names as bullets.
"""


def ai_generate_answer(question: str, people_data: List[Any]) -> str:
    """
    Uses OpenAI to convert fetched JIRA + GitHub data for one or more people
    into a concise Markdown report.
    """

    client = _get_client()

    payload = {
        "question": question,
        "people": [
            {
                "person_name": p["person_name"],
                "jira_issues": p.get("jira_issues", []),
                "github_activity": p.get("github_data", {}),
            }
            for p in people_data
        ],
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Create the Markdown report for the question below using ONLY the JSON.\n\n"
                    f"Question: {question}\n\n"
                    "JSON:\n"
                    f"{json.dumps(payload, indent=2)}"
                ),
            },
        ],
        temperature=0.2,
    )

    text = response.choices[0].message.content or ""
    return text.strip()


GITHUB_ONLY_PROMPT = """You are an AI assistant. Output ONLY GitHub activity.
- Use VALID MARKDOWN.
- For a SINGLE person: # Summary, ## GitHub, ### Open Pull Requests, ### Commits, ### Recent Repositories.
- For MULTIPLE people: # Summary, then ## PERSON_NAME for each with ### Open Pull Requests, ### Commits subsections.
- Use '-' for bullets. INCLUDE clickable links: [TITLE](url) for PRs, [MESSAGE](url) for commits.
- Use ONLY the provided data. Do NOT invent anything."""

JIRA_ONLY_PROMPT = """You are an AI assistant. Output ONLY JIRA tickets.
- Use VALID MARKDOWN.
- For a SINGLE person: # Summary, ## JIRA.
- For MULTIPLE people: # Summary, then ## PERSON_NAME for each with their JIRA tickets.
- Use '-' for bullets. INCLUDE clickable links: [KEY](url) — SUMMARY (STATUS)
- Use ONLY the provided data. Do NOT invent anything."""


def ai_generate_github_only(question: str, people_data: List[Any]) -> str:
    client = _get_client()
    payload = {
        "question": question,
        "people": [
            {"person_name": p["person_name"], "github_activity": p.get("github_data", {})}
            for p in people_data
        ],
    }
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": GITHUB_ONLY_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nJSON:\n{json.dumps(payload, indent=2)}",
            },
        ],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def ai_generate_jira_only(question: str, people_data: List[Any]) -> str:
    client = _get_client()
    payload = {
        "question": question,
        "people": [
            {"person_name": p["person_name"], "jira_issues": p.get("jira_issues", [])}
            for p in people_data
        ],
    }
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": JIRA_ONLY_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nJSON:\n{json.dumps(payload, indent=2)}",
            },
        ],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def ai_generate_general_answer(
    question: str,
    intent: str,
    conversation_history: Optional[List[dict[str, str]]] = None,
) -> str:
    """
    Handles general chat and other non-team-activity questions.
    Uses conversation_history for follow-ups (e.g. "my friend is Jeff" then
    "what is my friend's name?").
    """
    client = _get_client()
    system = (
        "You are a helpful, friendly chatbot. Answer the user's question "
        "conversationally. Be concise. Use markdown if it helps readability. "
        "Use information from earlier in the conversation when the user asks "
        "follow-up questions (e.g. if they said 'my friend is Jeff' and now ask "
        "'what is my friend's name?', answer 'Jeff')."
    )

    messages = [{"role": "system", "content": system}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )

    text = response.choices[0].message.content or ""
    return text.strip()


def ai_generate_weather_answer(question: str, weather_data: Any) -> str:
    """Format real weather data into a friendly markdown response."""
    client = _get_client()
    system = (
        "You are a helpful chatbot. Format the provided weather data into a "
        "friendly, conversational response. Use markdown. Include: location, "
        "temperature (show both °C and °F), conditions, humidity if present, "
        "and wind. Be concise."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Question: {question}\n\nWeather data:\n{json.dumps(weather_data, indent=2)}",
            },
        ],
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    return text.strip()


def ai_generate_date_answer(question: str, date_info: Any) -> str:
    """Format date/time info into a friendly markdown response."""
    client = _get_client()
    system = (
        "You are a helpful chatbot. Format the provided date/time information "
        "into a friendly, conversational response. Use markdown. Be concise."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Question: {question}\n\nDate/time data:\n{json.dumps(date_info, indent=2)}",
            },
        ],
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    return text.strip()
