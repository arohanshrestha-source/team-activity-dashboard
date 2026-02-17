"""
Detects user intent from the question so the chatbot can respond appropriately.
"""
from typing import Literal

from app.utils.query_parser import extract_person_key, extract_jira_issue_key

Intent = Literal[
    "weather", "date", "team_directory", "jira_issue_lookup",
    "github_only", "jira_only", "team_activity", "general_chat",
]


def detect_intent(question: str) -> Intent:
    """
    Classify user intent. Uses keyword heuristics first (fast, no API),
    falls back to AI if ambiguous.
    """
    q = question.lower().strip()

    # Identity/self-intro: user stating their name, not asking about work
    identity_phrases = ["my name is", "my name's", "i am", "i'm ", "call me"]
    if any(p in q for p in identity_phrases):
        return "general_chat"

    # Fast keyword-based detection
    weather_words = ["weather", "temperature", "forecast", "rain", "snow", "sunny", "how hot", "how cold"]
    if any(w in q for w in weather_words):
        return "weather"

    date_words = ["date", "what day", "what's the date", "today's date", "current date", "what time", "current time"]
    if any(w in q for w in date_words):
        return "date"

    # Team directory: list people on the team (names only, no activities)
    team_dir_phrases = [
        "team directory", "team members", "list people", "name all people",
        "name the people", "name everyone on the team", "who is on the team",
        "who's on the team", "people on the team", "who are the team members",
        "team roster", "list team", "show team", "team list", "all team members",
        "who are all the users", "who are the users", "list all users",
        "list users", "show all users", "show users", "what users are there",
        "names of all users", "who are the people", "list all people",
    ]
    if any(p in q for p in team_dir_phrases):
        return "team_directory"

    # JIRA issue lookup: "what is SAM1-8?", "tell me about KAN-2", "what project is SAM1-8?"
    issue_lookup_phrases = [
        "what is ", "what's ", "tell me about ", "tell me more about ",
        "what project is ", "what's the project for ", "details for ",
        "info on ", "information on ", "describe ", "explain ",
    ]
    issue_key = extract_jira_issue_key(question)
    if issue_key and any(p in q for p in issue_lookup_phrases):
        return "jira_issue_lookup"

    github_words = ["github", "git hub", "pull request", "prs", "commits", "repos", "repositories"]
    jira_words = ["jira", "jira ticket", "jira issue", "ticket", "assigned to"]
    # Specific phrases that indicate team/work questions (not broad ones like "what is")
    team_phrases = ["working on", "activity", "these days", "up to", "doing", "work", "status"]

    # "The team" / team activities / casual: "what is the team doing?", "team activities", "team, what they doin?"
    team_activity_phrases = [
        "the team doing", "team doing", "team activities", "team activity",
        "what the team", "what's the team", "what is the team", "how's the team",
        "team work", "team status", "team up to", "team , what", "team, what",
        "what they doin", "what they doing", "team what they",
    ]

    has_github = any(w in q for w in github_words)
    has_jira = any(w in q for w in jira_words)
    has_team_phrase = any(w in q for w in team_phrases)
    has_team_activity_phrase = any(p in q for p in team_activity_phrases)
    has_known_person = extract_person_key(question) is not None

    # GitHub only: mentions github/prs/commits but NOT jira
    if has_github and not has_jira:
        return "github_only"

    # Jira only: mentions jira/tickets but NOT github
    if has_jira and not has_github:
        return "jira_only"

    # Team activity: explicit work phrases, "the team" / team activities, known person, or both github+jira
    if has_team_phrase or has_team_activity_phrase or has_known_person or (has_github and has_jira):
        return "team_activity"

    # Default: general chat (could be weather, small talk, etc.)
    return "general_chat"
