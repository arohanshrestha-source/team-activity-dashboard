import os

# Bind to the port provided by the platform (Railway/Render/Heroku)
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# IMPORTANT:
# If REDIS_URL is not set, conversation memory / cache may be in-memory only.
# With multiple workers, users can hit different workers and "lose" memory.
# So default to 1 worker unless Redis is configured.
workers = 2 if os.getenv("REDIS_URL") else 1

# Reasonable defaults for small apps
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
