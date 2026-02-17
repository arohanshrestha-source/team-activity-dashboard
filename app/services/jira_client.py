import requests
from typing import Any, Dict, List, Optional

from app.config import get_settings

def _jira_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json",
    }


def _check_jira_config():
    """Raise a clear error if JIRA is not configured (e.g. missing env vars on Railway)."""
    s = get_settings()
    base = (s.jira_base_url or "").strip()
    if not base or not base.startswith(("http://", "https://")):
        raise RuntimeError(
            "JIRA_BASE_URL is not set or invalid. "
            "On Railway: set it in your service Variables. "
            "Locally: add JIRA_BASE_URL=https://your-domain.atlassian.net to .env"
        )


def get_issue_by_key(issue_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single JIRA issue by key (e.g. SAM1-8, KAN-2).
    Returns normalized dict with key, summary, status, project, description, url, assignee; or None if not found.
    """
    _check_jira_config()
    s = get_settings()
    url = f"{s.jira_base_url.rstrip('/')}/rest/api/3/issue/{issue_key}"
    params = {"fields": "summary,status,project,description,assignee,updated,created"}
    try:
        resp = requests.get(
            url,
            headers=_jira_headers(),
            auth=(s.jira_email, s.jira_api_token),
            params=params,
            timeout=15,
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise RuntimeError(f"JIRA request failed ({resp.status_code}): {resp.text}")
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"JIRA request failed: {e}") from e

    key = data.get("key")
    fields = data.get("fields", {})
    project = fields.get("project") or {}
    project_name = project.get("name") or project.get("key") or ""
    project_key = project.get("key") or ""
    assignee = fields.get("assignee") or {}
    assignee_name = assignee.get("displayName") or assignee.get("emailAddress") or "Unassigned"

    # Description can be ADF (Atlassian Document Format); use plain if present, else truncate
    desc = fields.get("description")
    if isinstance(desc, dict):
        # ADF: try to get plain text from content
        content = desc.get("content", [])
        parts = []
        for block in content:
            if block.get("type") == "paragraph":
                for c in block.get("content", []):
                    if c.get("type") == "text":
                        parts.append(c.get("text", ""))
        description_plain = " ".join(parts).strip() if parts else ""
    elif isinstance(desc, str):
        description_plain = desc.strip()
    else:
        description_plain = ""

    return {
        "key": key,
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "project_key": project_key,
        "project_name": project_name,
        "description": description_plain,
        "assignee": assignee_name,
        "updated": fields.get("updated"),
        "created": fields.get("created"),
        "url": f"{s.jira_base_url.rstrip('/')}/browse/{key}" if key else None,
    }


def get_assigned_issues(assignee_email: str, max_results: int = 10) -> List[Dict[str, Any]]:
    _check_jira_config()
    s = get_settings()

    # NEW endpoint (old /search is removed)
    url = f"{s.jira_base_url.rstrip('/')}/rest/api/3/search/jql"

    jql = f'assignee = "{assignee_email}" AND statusCategory != Done ORDER BY updated DESC'

    params = {
        "jql": jql,
        "maxResults": max_results,
        # fields can be comma-separated string
        "fields": "summary,status,updated",
    }

    resp = requests.get(
        url,
        headers=_jira_headers(),
        auth=(s.jira_email, s.jira_api_token),
        params=params,
        timeout=20,
    )

    if resp.status_code >= 400:
        raise RuntimeError(f"JIRA request failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    issues = data.get("issues", [])

    normalized = []
    for issue in issues:
        fields = issue.get("fields", {})
        key = issue.get("key")
        normalized.append({
            "key": key,
            "summary": fields.get("summary"),
            "status": (fields.get("status") or {}).get("name"),
            "updated": fields.get("updated"),
            "url": f"{s.jira_base_url.rstrip('/')}/browse/{key}" if key else None,
        })

    return normalized
