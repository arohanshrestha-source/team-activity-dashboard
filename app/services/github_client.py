import requests
from typing import Any, Dict, List, Set

from app.config import get_settings

GITHUB_API = "https://api.github.com"

def _gh_headers() -> Dict[str, str]:
    s = get_settings()
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {s.github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "team-activity-monitor",
    }

def get_recent_commits_from_events(username: str, max_events: int = 30) -> List[Dict[str, Any]]:
    """
    Uses public user events to find recent commits (PushEvent).
    Works best if the user's activity is public.
    """
    url = f"{GITHUB_API}/users/{username}/events/public"
    resp = requests.get(url, headers=_gh_headers(), params={"per_page": max_events}, timeout=20)

    if resp.status_code >= 400:
        raise RuntimeError(f"GitHub events request failed ({resp.status_code}): {resp.text}")

    events = resp.json()
    commits: List[Dict[str, Any]] = []

    for e in events:
        if e.get("type") != "PushEvent":
            continue

        repo_name = (e.get("repo") or {}).get("name")
        payload = e.get("payload") or {}
        for c in payload.get("commits", [])[:10]:
            sha = c.get("sha")
            msg = c.get("message")
            # Link format for commit URL in repo
            url = f"https://github.com/{repo_name}/commit/{sha}" if repo_name and sha else None
            commits.append({
                "repo": repo_name,
                "sha": sha,
                "message": msg,
                "url": url,
            })

    # keep it reasonable
    return commits[:20]

def get_open_pull_requests(username: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Uses GitHub Search API to find open PRs authored by the user.
    """
    q = f"type:pr author:{username} is:open"
    url = f"{GITHUB_API}/search/issues"
    resp = requests.get(url, headers=_gh_headers(), params={"q": q, "per_page": max_results}, timeout=20)

    if resp.status_code >= 400:
        raise RuntimeError(f"GitHub PR search failed ({resp.status_code}): {resp.text}")

    items = resp.json().get("items", [])
    prs: List[Dict[str, Any]] = []

    for pr in items:
        prs.append({
            "title": pr.get("title"),
            "repo": (pr.get("repository_url") or "").replace("https://api.github.com/repos/", ""),
            "state": pr.get("state"),
            "updated_at": pr.get("updated_at"),
            "url": pr.get("html_url"),
        })

    return prs

def get_recent_repos(username: str, max_events: int = 30) -> List[str]:
    """
    Derives recent repos from public events.
    """
    url = f"{GITHUB_API}/users/{username}/events/public"
    resp = requests.get(url, headers=_gh_headers(), params={"per_page": max_events}, timeout=20)

    if resp.status_code >= 400:
        raise RuntimeError(f"GitHub events request failed ({resp.status_code}): {resp.text}")

    events = resp.json()
    repos: Set[str] = set()

    for e in events:
        repo_name = (e.get("repo") or {}).get("name")
        if repo_name:
            repos.add(repo_name)

    return sorted(list(repos))[:15]

def get_github_activity_summary(username: str) -> Dict[str, Any]:
    """
    One call used by your route: commits + PRs + repos.
    """
    commits = get_recent_commits_from_events(username)
    prs = get_open_pull_requests(username)
    repos = get_recent_repos(username)
    return {
        "username": username,
        "recent_commits": commits,
        "open_pull_requests": prs,
        "recent_repos": repos,
    }
