from typing import Any, Dict, List

def build_answer_md(person_key: str,
                    jira_issues: List[Dict[str, Any]],
                    github_data: Dict[str, Any]) -> str:
    name = person_key.capitalize()

    parts = []

    # -------------------------
    # Summary
    # -------------------------
    parts.append(f"# Summary")
    parts.append(
        f"- {name} is currently working on activity across JIRA and GitHub."
    )

    # -------------------------
    # JIRA Section
    # -------------------------
    parts.append("\n## JIRA")

    if not jira_issues:
        parts.append("- No active assigned issues found.")
    else:
        for issue in jira_issues[:5]:
            key = issue.get("key", "")
            summary = issue.get("summary", "")
            status = issue.get("status", "")
            url = issue.get("url", "")
            if url:
                parts.append(f"- [{key}]({url}): **{summary}** ({status})")
            else:
                parts.append(f"- **{key}**: {summary} ({status})")

    # -------------------------
    # GitHub Section
    # -------------------------
    parts.append("\n## GitHub")

    prs = github_data.get("open_pull_requests", [])
    commits = github_data.get("recent_commits", [])
    repos = github_data.get("recent_repos", [])

    # ---- PRs
    parts.append("\n### Open Pull Requests")
    if prs:
        for pr in prs[:5]:
            title = pr.get("title", "")
            repo = pr.get("repo", "")
            url = pr.get("url", "")
            if url:
                parts.append(f"- **{title}** ({repo})  \n  [View PR]({url})")
            else:
                parts.append(f"- **{title}** ({repo})")
    else:
        parts.append("- No open pull requests found.")

    # ---- Commits
    parts.append("\n### Commits")
    if commits:
        for c in commits[:5]:
            msg = (c.get("message") or "").split("\n")[0]
            repo = c.get("repo", "")
            url = c.get("url", "")
            if url:
                parts.append(f"- {msg} ({repo})  \n  [View Commit]({url})")
            else:
                parts.append(f"- {msg} ({repo})")
    else:
        parts.append("- No recent commits found.")

    # ---- Repos
    parts.append("\n### Recent Repositories")
    if repos:
        for r in repos[:5]:
            parts.append(f"- {r}")
    else:
        parts.append("- No recent repositories found.")

    return "\n".join(parts)


def build_answer_md_multi(people_data: List[Dict[str, Any]]) -> str:
    """Build markdown report for multiple people."""
    parts = ["# Summary"]
    names = [p["person_name"] for p in people_data]
    parts.append(f"- Activity for: {', '.join(names)}.")

    for p in people_data:
        name = p["person_name"]
        jira_issues = p.get("jira_issues") or []
        github_data = p.get("github_data") or {}

        parts.append(f"\n## {name}")
        parts.append("\n### JIRA")
        if not jira_issues:
            parts.append("- No active assigned issues found.")
        else:
            for issue in jira_issues[:5]:
                key = issue.get("key", "")
                summary = issue.get("summary", "")
                status = issue.get("status", "")
                url = issue.get("url", "")
                if url:
                    parts.append(f"- [{key}]({url}): **{summary}** ({status})")
                else:
                    parts.append(f"- **{key}**: {summary} ({status})")

        parts.append("\n### GitHub")
        prs = github_data.get("open_pull_requests", [])
        commits = github_data.get("recent_commits", [])
        parts.append("Open Pull Requests:")
        if prs:
            for pr in prs[:5]:
                title = pr.get("title", "")
                repo = pr.get("repo", "")
                url = pr.get("url", "")
                if url:
                    parts.append(f"- **{title}** ({repo})  \n  [View PR]({url})")
                else:
                    parts.append(f"- **{title}** ({repo})")
        else:
            parts.append("- No open pull requests found.")
        parts.append("Commits:")
        if commits:
            for c in commits[:5]:
                msg = (c.get("message") or "").split("\n")[0]
                repo = c.get("repo", "")
                url = c.get("url", "")
                if url:
                    parts.append(f"- {msg} ({repo})  \n  [View Commit]({url})")
                else:
                    parts.append(f"- {msg} ({repo})")
        else:
            parts.append("- No recent commits found.")

    return "\n".join(parts)
