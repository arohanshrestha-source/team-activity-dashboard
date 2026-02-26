const qEl = document.getElementById("q");
const chatEl = document.getElementById("chat");
const btn = document.getElementById("askBtn");

const API_BASE = (document.querySelector('meta[name="api-base"]')?.getAttribute('content') || '').replace(/\/$/, '');

function getSessionId() {
  let id = sessionStorage.getItem('team-activity-session');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now();
    sessionStorage.setItem('team-activity-session', id);
  }
  return id;
}

// All messages in order: { role: 'user' | 'assistant', content: string, links?: array }
let messages = [];

function mdToHtml(md) {
  if (typeof marked !== "undefined" && marked && typeof marked.parse === "function") {
    return marked.parse(md || "");
  }
  return (md || "").replace(/</g, "&lt;");
}

function getWelcomeHtml() {
  return `
    <div class="welcome">
      <p class="intro">Ask anything below. You can ask about team activity, JIRA issues, GitHub PRs, weather, or general questions.</p>
      <div class="category">
        <h2>Team &amp; activity</h2>
        <ul>
          <li><strong>What is [name] working on?</strong> — One person's JIRA + GitHub</li>
          <li><strong>What is the team doing?</strong> / <strong>Team activities</strong> — Everyone's activity</li>
          <li><strong>Who are all the users?</strong> — List of team members</li>
          <li><strong>What about Mike?</strong> / <strong>and Sarah?</strong> — Follow-up after a previous question</li>
        </ul>
      </div>
      <div class="category">
        <h2>JIRA</h2>
        <ul>
          <li><strong>What is SAM1-8?</strong> / <strong>Tell me about KAN-2</strong> — Details for a specific issue</li>
          <li><strong>What JIRA tickets is [name] on?</strong> — Someone's assigned issues</li>
        </ul>
      </div>
      <div class="category">
        <h2>GitHub</h2>
        <ul>
          <li><strong>Details about PR #5 in owner/repo</strong> — Or paste a GitHub PR URL</li>
          <li><strong>Show me [name]'s GitHub activity</strong> — PRs, commits, repos</li>
        </ul>
      </div>
      <div class="category">
        <h2>Other</h2>
        <ul>
          <li><strong>Weather in Austin</strong> / <strong>Forecast for Paris</strong></li>
          <li><strong>What's the date?</strong> / <strong>What time is it?</strong></li>
          <li>General chat — e.g. <strong>My friend's name is Jeff</strong> → <strong>What is my friend's name?</strong></li>
        </ul>
      </div>
    </div>
  `;
}

function renderMessages() {
  if (messages.length === 0) {
    chatEl.innerHTML = getWelcomeHtml();
    return;
  }
  chatEl.innerHTML = messages
    .map((m) => {
      const isThinking = m.role === "assistant" && m.content === "**Thinking...**";
      const bubbleClass = isThinking ? "message-bubble message-thinking" : "message-bubble";
      const htmlContent = mdToHtml(m.content);
      const linksHtml =
        m.links && m.links.length > 0
          ? `<div class="message-links">${m.links.map((l) => `<a href="${l.url}" target="_blank" rel="noopener">${l.label || l.url}</a>`).join("")}</div>`
          : "";
      return `<div class="message ${m.role} ${isThinking ? "thinking" : ""}"><div class="${bubbleClass}">${htmlContent}${linksHtml}</div></div>`;
    })
    .join("");
  scrollToBottom();
}

function scrollToBottom() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

function appendMessage(role, content, links) {
  messages.push({ role, content, links: links || [] });
  renderMessages();
}

function replaceLastAssistantMessage(content, links) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") {
      messages[i].content = content;
      messages[i].links = links || [];
      break;
    }
  }
  renderMessages();
}

async function ask() {
  const question = qEl.value.trim();
  if (!question) return;

  qEl.value = "";
  appendMessage("user", question);
  appendMessage("assistant", "**Thinking...**");
  btn.disabled = true;

  try {
    const url = API_BASE ? `${API_BASE}/ask` : "/ask";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: getSessionId() }),
    });

    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch (_) {
      replaceLastAssistantMessage(
        "**Request failed:** Server returned invalid JSON. Is the backend running? Check that api-base points to http://127.0.0.1:5000"
      );
      return;
    }

    if (!res.ok) {
      replaceLastAssistantMessage(`**Error:** ${data.error || "Unknown error"}`);
      return;
    }

    const md = data.answer_md || data.answer || "No answer returned.";
    replaceLastAssistantMessage(md, data.links || []);
  } catch (e) {
    replaceLastAssistantMessage(`**Request failed:** ${String(e)}`);
  } finally {
    btn.disabled = false;
    qEl.focus();
  }
}

btn.addEventListener("click", ask);
qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    ask();
  }
});
