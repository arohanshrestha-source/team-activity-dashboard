# Team Activity Monitor

A lightweight web application that answers natural-language questions about what team members are working on by integrating JIRA, GitHub, weather, date/time, and AI-powered general chat.

---

## Features

- **Chat-style web UI** – Scrolling conversation history (like ChatGPT); previous questions and answers stay visible as you ask more.
- **JIRA integration** – Fetches assigned issues and status; **look up any issue by key** (e.g. “What is SAM1-8?”, “What project is KAN-2?”).
- **GitHub integration** – Fetches pull requests, commits, and repositories.
- **Weather** – Real-time weather via Open-Meteo (free, no API key).
- **Date/time** – Current date and time.
- **General chat** – AI answers questions and remembers context for follow-ups.
- **Team directory** – “Who are all the users?” lists team members (no activity fetch).
- **Multi-user queries** – Get activity for multiple people or all users in one request.
- **Follow-ups** – “What about Mike?”, “and Sarah?” after an initial query; general chat remembers prior context.
- **Response cache** – Faster repeated questions (5-min TTL; in-memory or Redis).
- **Conversation memory** – Session-based context for follow-ups (30-min TTL; in-memory or Redis).

---

## Tech Stack

- **Backend:** Python + Flask
- **Frontend:** HTML, CSS, JavaScript; [marked.js](https://marked.js.org/) for Markdown in chat
- **APIs:** JIRA REST API (search + get issue by key), GitHub REST API, Open-Meteo (weather)
- **AI:** OpenAI GPT-4o-mini
- **Config:** python-dotenv
- **Optional:** Redis (for persistent cache and conversation memory); Docker Compose for running Redis

---

## Project Structure

```
team-activity-monitor/
├── app/
│   ├── main.py              # Flask app entry point (serves API + optional static frontend)
│   ├── config.py            # Settings from .env (includes REDIS_URL)
│   ├── routes/
│   │   └── api.py           # API routes (/ask, /health, /jira/..., /github/..., etc.)
│   ├── services/
│   │   ├── ai_client.py     # OpenAI integration
│   │   ├── github_client.py # GitHub API
│   │   ├── jira_client.py   # JIRA API (assigned issues + get issue by key)
│   │   ├── weather_client.py# Open-Meteo weather
│   │   ├── redis_client.py  # Optional Redis connection (cache + memory)
│   │   ├── conversation_memory.py  # Session context (in-memory or Redis)
│   │   └── response_cache.py      # Response cache (in-memory or Redis)
│   └── utils/
│       ├── intent_detector.py      # Classify question type (weather, jira_issue_lookup, etc.)
│       ├── query_parser.py         # Extract people, JIRA keys, "all users"
│       ├── follow_up_resolver.py   # Resolve follow-up questions
│       ├── response_generator.py   # Markdown formatting
│       └── date_utils.py           # Date/time helpers
├── public/
│   ├── index.html           # Chat UI (scrollable message history)
│   └── script.js            # Frontend: send question, append messages, render Markdown
├── tests/                   # Pytest tests for CI
│   ├── conftest.py
│   └── test_app.py
├── .github/workflows/
│   └── ci.yml               # GitHub Actions: install, run tests
├── docker-compose.yml       # Redis service for persistent cache/memory
├── Procfile                 # For Railway, Render, Heroku (web: python -m app.main)
├── .env                     # API keys (not committed)
├── requirements.txt
├── requirements-dev.txt     # requirements.txt + pytest (for CI/local tests)
└── README.md
```

---

## Setup

### 1. Clone and install dependencies

```bash
python -m venv venv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Create `.env`

```env
# JIRA (required for JIRA queries and issue lookup)
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=...

# GitHub (required for GitHub queries)
GITHUB_TOKEN=ghp_...

# OpenAI (required for AI formatting and general chat)
OPENAI_API_KEY=sk-...

# Optional: Weather default location
WEATHER_DEFAULT_CITY=Austin
WEATHER_LAT=30.2672
WEATHER_LON=-97.7431

# Optional: CORS origins when using split frontend/backend
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional: Redis for persistent response cache and conversation memory (see Docker section)
REDIS_URL=redis://localhost:6379/0
```

### 3. Configure users

Edit `app/utils/query_parser.py` and add people to `USER_DIRECTORY` (with optional `aliases`):

```python
USER_DIRECTORY = {
    "arohan": {"aliases": ["arohan"], "jira": "arohan@example.com", "github": "arohan"},
    "mike": {"aliases": ["mike"], "jira": "mike@example.com", "github": "mike"},
    # ...
}
```

---

## Run the Application

### Single server (default)

Frontend and backend run together; the app serves the chat UI and the API from one process. No environment variable needed.

```bash
python -m app.main
```

Open **http://127.0.0.1:5000**. You get the chatbot UI with scrolling conversation history.

### Split (two servers)

Use this if you want the frontend and backend on different ports (e.g. separate frontend dev server).

**Terminal 1 – Backend (API only):**
```bash
# Disable serving static files so only the API runs
# Windows PowerShell:
$env:USE_STATIC="0"
python -m app.main

# macOS/Linux:
USE_STATIC=0 python -m app.main
```
Backend runs on http://127.0.0.1:5000

**Terminal 2 – Frontend:**
```bash
python -m http.server 3000 --directory public
```
Frontend runs on http://localhost:3000

In `public/index.html`, the API base should point to the backend:
```html
<meta name="api-base" content="http://127.0.0.1:5000" />
```

Then open http://localhost:3000

---

## Example Queries

| Type | Examples |
|------|----------|
| Team activity | "What is Arohan working on?" |
| Multi-user | "Get Arohan and Mike's activities" |
| All users | "Get activities for all users" |
| Team directory (names only) | "Who are all the users?" / "List all users" |
| JIRA issue lookup | "What is SAM1-8?" / "What project is KAN-2?" / "Tell me about SAM1-11" |
| GitHub only | "Show me Sarah's GitHub activity" |
| JIRA only | "What JIRA tickets is Mike on?" |
| Weather | "Weather in Austin" / "Forecast for Paris" |
| Date/time | "What's the date?" / "What time is it?" |
| General chat | "My friend's name is Jeff" → "What is my friend's name?" |
| Follow-ups | "What about Mike?" / "and Sarah?" |

---

## Backend database (Docker + Redis)

You can run **Redis** in Docker to persist the response cache and conversation memory across restarts.

### 1. Start Redis

From the project root:

```bash
docker compose up -d
```

Redis listens on `localhost:6379`. Data is stored in a Docker volume (`redis_data`).

### 2. Point the app at Redis

In your `.env`:

```env
REDIS_URL=redis://localhost:6379/0
```

### 3. Run the app as usual

With `REDIS_URL` set, the app uses Redis for:

- **Response cache** – Cached answers (5‑min TTL) survive restarts.
- **Conversation memory** – Session context and chat history (30‑min TTL) survive restarts.

Without `REDIS_URL`, the app uses in-memory storage only (data is lost on server restart).

### Useful Docker commands

```bash
# Start Redis in the background
docker compose up -d

# View Redis logs
docker compose logs -f redis

# Stop Redis (data in volume is kept)
docker compose down

# Stop and remove the data volume
docker compose down -v
```

### Inspecting what’s stored in Redis

```bash
docker exec -it team-activity-monitor-redis redis-cli
```

Then for example: `KEYS *`, `KEYS rc:*`, `KEYS session:*`, `GET <key>`, `TTL <key>`, `quit`.

---

## CI/CD and deployment

### CI (GitHub Actions)

On every **push** and **pull_request** to `main` or `master`, the workflow in `.github/workflows/ci.yml` runs:

1. Checkout repo
2. Set up Python 3.11
3. Install dependencies (`pip install -r requirements-dev.txt`)
4. Run tests (`pytest tests/ -v`)

To run the same locally:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Deployment (CD)

The app is ready to deploy to any host that runs Python and sets environment variables. The server binds to `0.0.0.0` and uses the **PORT** environment variable (default 5000), so it works on Railway, Render, Fly.io, Heroku, and similar platforms.

**Required env vars in production:**

- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `GITHUB_TOKEN`
- `OPENAI_API_KEY`

**Optional:** `REDIS_URL`, `WEATHER_DEFAULT_CITY`, `WEATHER_LAT`, `WEATHER_LON`, `CORS_ORIGINS`, `FLASK_DEBUG`

**Option A – Railway**

1. Push the repo to GitHub and connect the repo in [Railway](https://railway.app).
2. Create a new project from the repo; Railway will detect the `Procfile` and run `web: python -m app.main`.
3. In the service **Variables**, add all required env vars (and optional `REDIS_URL` if you add a Redis plugin).
4. Deploy; Railway assigns a URL and sets `PORT` automatically.

**Option B – Render**

1. Push to GitHub and connect at [Render](https://render.com).
2. New **Web Service**, connect the repo.
3. **Build command:** `pip install -r requirements.txt` (or leave default).
4. **Start command:** `python -m app.main` (or use the Procfile).
5. Add env vars in the Render dashboard (including secrets for JIRA, GitHub, OpenAI). Optionally add a **Redis** instance and set `REDIS_URL`.
6. Deploy; Render sets `PORT` automatically.

**Option C – Fly.io**

1. Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/) and run `fly launch` in the project root (create `fly.toml` if needed).
2. Set secrets: `fly secrets set JIRA_BASE_URL=... JIRA_EMAIL=...` (and the rest).
3. Deploy with `fly deploy`. Fly sets `PORT=8080` by default; the app reads `PORT` from the env.

**Option D – Heroku**

1. Create an app and connect GitHub. Heroku uses the `Procfile` (`web: python -m app.main`).
2. Set config vars (env) in Settings → Reveal Config Vars: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, and optionally `REDIS_URL` (e.g. from Heroku Redis add-on).
3. Enable automatic deploys from the `main` branch if desired.

**Frontend (api-base):** After deployment, set your app’s public URL in `public/index.html` if you ever build the frontend separately, or rely on the single-server mode (default) so the same origin is used and no change is needed.

---

## UI overview

- **Header** – App title.
- **Chat area** – Scrollable list of messages: your questions on the right (dark bubbles), answers on the left (white bubbles). Markdown and links are rendered. New messages appear at the bottom with auto-scroll.
- **Input** – Text field and Send button at the bottom. Enter sends; session is kept in the browser for follow-ups and conversation memory.

---

## Storage note (without Redis)

If you do **not** set `REDIS_URL`, conversation memory and response cache are **in-memory only** (Python dicts). Data is lost on server restart. The chat UI still keeps the visible conversation in the browser until you refresh or close the tab.
