# app/routes/api.py

from flask import Blueprint, jsonify, request, current_app

from app.config import get_settings
from app.services.jira_client import get_assigned_issues, get_issue_by_key
from app.services.github_client import get_github_activity_summary
from app.utils.query_parser import (
    USER_DIRECTORY,
    extract_jira_issue_key,
    extract_mentioned_unknown_person,
    extract_person_keys,
    get_accounts,
    get_default_person,
)
from app.utils.response_generator import build_answer_md, build_answer_md_multi
from app.utils.intent_detector import detect_intent

from app.services.ai_client import (
    ai_generate_answer,
    ai_generate_date_answer,
    ai_generate_general_answer,
    ai_generate_github_only,
    ai_generate_jira_only,
    ai_generate_weather_answer,
)
from app.services.weather_client import get_weather_for_question
from app.utils.date_utils import get_current_datetime_info
from app.services.conversation_memory import (
    append_exchange as append_memory_exchange,
    get_context as get_memory_context,
    get_conversation_history as get_memory_history,
    set_context as set_memory_context,
)
from app.services.response_cache import get as get_cached_response, set as set_cached_response
from app.utils.follow_up_resolver import resolve_follow_up

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api_bp.route("/config-check", methods=["GET"])
def config_check():
    s = get_settings()
    return jsonify({
        "jira_base_url_set": bool(s.jira_base_url),
        "jira_email_set": bool(s.jira_email),
        "jira_api_token_set": bool(s.jira_api_token),
        "github_token_set": bool(s.github_token),
        "openai_api_key_set": bool(s.openai_api_key),
    })


@api_bp.route("/routes", methods=["GET"])
def routes():
    return jsonify({
        "routes": sorted([str(r) for r in current_app.url_map.iter_rules()])
    })


# -----------------------
# JIRA
# -----------------------
@api_bp.route("/jira/assigned", methods=["GET"])
def jira_assigned():
    assignee = request.args.get("assignee")
    if not assignee:
        return jsonify({"error": "Missing query param: assignee"}), 400

    issues = get_assigned_issues(assignee_email=assignee, max_results=10)
    return jsonify({"assignee": assignee, "issues": issues})


# -----------------------
# GitHub
# -----------------------
@api_bp.route("/github/activity", methods=["GET"])
def github_activity():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "Missing query param: user"}), 400

    data = get_github_activity_summary(user)
    return jsonify(data)


@api_bp.route("/github/token-check", methods=["GET"])
def github_token_check():
    s = get_settings()
    token = s.github_token or ""
    return jsonify({
        "github_token_set": bool(token),
        "github_token_prefix": token[:10],
        "github_token_length": len(token),
    })


# -----------------------
# OpenAI checks
# -----------------------
@api_bp.route("/openai-key-check", methods=["GET"])
def openai_key_check():
    s = get_settings()
    k = s.openai_api_key or ""
    return jsonify({
        "openai_key_set": bool(k),
        "prefix": k[:3],
        "length": len(k),
    })


@api_bp.route("/ai-check", methods=["GET"])
def ai_check():
    try:
        _ = ai_generate_answer(
            question="Test",
            people_data=[{"person_name": "Test User", "jira_issues": [], "github_data": {}}],
        )
        return jsonify({"ai_ok": True})
    except Exception as e:
        print("OPENAI ERROR:", e)
        return jsonify({"ai_ok": False, "error": str(e)}), 500


# -----------------------
# Main chatbot endpoint
# -----------------------
@api_bp.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    session_id = (payload.get("session_id") or "").strip() or None

    if not question:
        return jsonify({"error": "Missing field: question"}), 400

    intent = detect_intent(question)

    # Weather: fetch real data, then format with AI
    if intent == "weather":
        try:
            weather_data = get_weather_for_question(question)
            answer_md = ai_generate_weather_answer(question, weather_data)
        except Exception as e:
            return jsonify({"error": f"Weather failed: {str(e)}"}), 502
        return jsonify({
            "answer_md": answer_md,
            "used_ai": True,
            "links": [],
        })

    # Date/time: use system datetime, format with AI
    if intent == "date":
        try:
            date_info = get_current_datetime_info()
            answer_md = ai_generate_date_answer(question, date_info)
        except Exception as e:
            return jsonify({"error": f"Date failed: {str(e)}"}), 502
        return jsonify({
            "answer_md": answer_md,
            "used_ai": True,
            "links": [],
        })

    # Team directory: list people from USER_DIRECTORY
    if intent == "team_directory":
        names = [key.capitalize() for key in USER_DIRECTORY.keys()]
        if not names:
            answer_md = "The team directory is empty."
        else:
            names_list = ", ".join(names)
            answer_md = (
                f"# Team Directory\n\n"
                f"The team has **{len(names)}** member(s):\n\n"
                f"- {names_list}"
            )
        return jsonify({
            "answer_md": answer_md,
            "used_ai": False,
            "links": [],
        })

    # JIRA issue lookup: "what is SAM1-8?", "what project is SAM1-8?"
    if intent == "jira_issue_lookup":
        issue_key = extract_jira_issue_key(question)
        if not issue_key:
            return jsonify({"error": "No JIRA issue key found in question."}), 400
        try:
            issue = get_issue_by_key(issue_key)
        except Exception as e:
            return jsonify({"error": f"JIRA failed: {str(e)}"}), 502
        if not issue:
            return jsonify({
                "error": f"Issue **{issue_key}** not found.",
                "hint": "Check the key or your JIRA access.",
            }), 404
        summary = issue.get("summary") or "—"
        status = issue.get("status") or "—"
        project_name = issue.get("project_name") or issue.get("project_key") or "—"
        project_key = issue.get("project_key") or ""
        description = (issue.get("description") or "").strip()
        assignee = issue.get("assignee") or "Unassigned"
        url = issue.get("url") or ""
        desc_preview = (description[:400] + "…") if len(description) > 400 else description
        answer_md = (
            f"# {issue_key}\n\n"
            f"**Summary:** {summary}\n\n"
            f"**Project:** {project_name}" + (f" ({project_key})" if project_key else "") + "\n\n"
            f"**Status:** {status}\n\n"
            f"**Assignee:** {assignee}\n\n"
        )
        if desc_preview:
            answer_md += f"**Description:**\n\n{desc_preview}\n\n"
        if url:
            answer_md += f"[Open in JIRA]({url})"
        links = [{"url": url, "label": f"View {issue_key} in JIRA"}] if url else []
        return jsonify({
            "answer_md": answer_md,
            "used_ai": False,
            "links": links,
        })

    # General chat: AI answers with conversation history for follow-ups
    if intent == "general_chat":
        try:
            history = get_memory_history(session_id) if session_id else []
            answer_md = ai_generate_general_answer(question, intent, conversation_history=history)
        except Exception as e:
            return jsonify({"error": f"AI failed: {str(e)}"}), 502
        if session_id:
            append_memory_exchange(session_id, question, answer_md)
        return jsonify({
            "answer_md": answer_md,
            "used_ai": True,
            "links": [],
        })

    # GitHub only, Jira only, or team activity: need one or more people
    person_keys = extract_person_keys(question)
    if not person_keys:
        unknown = extract_mentioned_unknown_person(question)
        if unknown:
            return jsonify({
                "error": f"'{unknown}' is not in the team directory.",
                "hint": "Add them to USER_DIRECTORY in app/utils/query_parser.py",
            }), 404
        default = get_default_person()
        person_keys = [default] if default else []

    # Follow-up resolution: use conversation context for "what about Mike?", "and Sarah?", etc.
    if session_id and person_keys:
        ctx = get_memory_context(session_id)
        if ctx:
            resolved_q, resolved_keys, was_resolved = resolve_follow_up(
                question,
                ctx.get("last_question", ""),
                ctx.get("last_intent", ""),
                ctx.get("last_person_keys", []),
            )
            if was_resolved and resolved_keys:
                question = resolved_q or question
                person_keys = resolved_keys

    if not person_keys:
        return jsonify({
            "error": "User not recognized in question",
            "hint": "Add the person to USER_DIRECTORY in app/utils/query_parser.py"
        }), 404

    # Response cache: avoid re-fetching same question (TTL 5 min)
    cached = get_cached_response(intent, person_keys, question)
    if cached:
        if session_id:
            set_memory_context(session_id, question, intent, person_keys)
        return jsonify(cached)

    # Fetch data for each person
    people_data = []
    all_links = []

    for person_key in person_keys:
        accounts = get_accounts(person_key)
        jira_issues = []
        gh_data = {}
        jira_id = accounts.get("jira") or ""
        gh_user = accounts.get("github") or ""

        if intent in ("jira_only", "team_activity") and jira_id:
            try:
                jira_issues = get_assigned_issues(assignee_email=jira_id, max_results=10)
            except Exception as e:
                return jsonify({"error": f"JIRA fetch failed for {person_key}: {str(e)}"}), 502

        if intent in ("github_only", "team_activity") and gh_user:
            try:
                gh_data = get_github_activity_summary(gh_user)
            except Exception as e:
                return jsonify({"error": f"GitHub fetch failed for {person_key}: {str(e)}"}), 502

        people_data.append({
            "person_key": person_key,
            "person_name": person_key.capitalize(),
            "jira_issues": jira_issues,
            "github_data": gh_data,
        })

        # Collect links for UI
        if intent in ("jira_only", "team_activity"):
            for i in jira_issues:
                if i.get("url"):
                    all_links.append({
                        "type": "jira",
                        "label": f"{person_key.capitalize()}: {i.get('key')} — {i.get('summary')}",
                        "url": i.get("url"),
                    })
        if intent in ("github_only", "team_activity"):
            for pr in (gh_data.get("open_pull_requests", []) if gh_data else []):
                if pr.get("url"):
                    all_links.append({
                        "type": "github_pr",
                        "label": f"{person_key.capitalize()}: {pr.get('repo')} — {pr.get('title')}",
                        "url": pr.get("url"),
                    })
            for c in (gh_data.get("recent_commits", []) if gh_data else []):
                if c.get("url"):
                    msg = (c.get("message") or "").split("\n")[0][:50]
                    all_links.append({
                        "type": "github_commit",
                        "label": f"{person_key.capitalize()}: {c.get('repo')} — {msg}…",
                        "url": c.get("url"),
                    })

    # Build answer based on intent
    used_ai = False
    if intent == "github_only":
        try:
            answer_md = ai_generate_github_only(question, people_data)
            used_ai = True
        except Exception as e:
            answer_md = _build_github_only_md_multi(people_data)
    elif intent == "jira_only":
        try:
            answer_md = ai_generate_jira_only(question, people_data)
            used_ai = True
        except Exception as e:
            answer_md = _build_jira_only_md_multi(people_data)
    else:
        # team_activity
        try:
            answer_md = ai_generate_answer(question, people_data)
            used_ai = True
        except Exception as e:
            print("AI FAILED, FALLING BACK:", e)
            answer_md = build_answer_md_multi(people_data)

    result = {
        "person": person_keys[0] if len(person_keys) == 1 else None,
        "people": person_keys,
        "answer_md": answer_md,
        "used_ai": used_ai,
        "links": all_links,
        "debug": {
            "intent": intent,
            "person_count": len(person_keys),
            "people": person_keys,
        },
    }

    # Store in memory and cache for follow-ups and faster repeats
    if session_id:
        set_memory_context(session_id, question, intent, person_keys)
    set_cached_response(intent, person_keys, question, result)

    return jsonify(result)


def _build_github_only_md_multi(people_data):
    """Fallback when AI fails for github_only (multi-person)."""
    parts = []
    for p in people_data:
        name = p["person_name"]
        gh_data = p.get("github_data") or {}
        parts.append(f"\n## {name}\n")
        parts.append("### Open Pull Requests")
        prs = gh_data.get("open_pull_requests", [])
        if prs:
            for pr in prs[:5]:
                parts.append(f"- {pr.get('repo')} — {pr.get('title')} ({pr.get('state')})")
        else:
            parts.append("- No open pull requests found.")
        parts.append("\n### Commits")
        commits = gh_data.get("recent_commits", [])
        if commits:
            for c in commits[:5]:
                parts.append(f"- {c.get('repo')} — {(c.get('message') or '').split(chr(10))[0]}")
        else:
            parts.append("- No recent commits found.")
    return "# GitHub Activity" + "\n".join(parts)


def _build_jira_only_md_multi(people_data):
    """Fallback when AI fails for jira_only (multi-person)."""
    parts = ["# JIRA Tickets", ""]
    for p in people_data:
        name = p["person_name"]
        jira_issues = p.get("jira_issues") or []
        parts.append(f"\n## {name}")
        if jira_issues:
            for i in jira_issues[:5]:
                parts.append(f"- {i.get('key')} — {i.get('summary')} ({i.get('status')})")
        else:
            parts.append("- No assigned issues found.")
    return "\n".join(parts)

  
