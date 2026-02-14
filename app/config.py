import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from project root
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

@dataclass
class Settings:
    jira_base_url: str = os.getenv("JIRA_BASE_URL", "")
    jira_email: str = os.getenv("JIRA_EMAIL", "")
    jira_api_token: str = os.getenv("JIRA_API_TOKEN", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # Optional: Redis URL for persistent response cache and conversation memory (e.g. redis://localhost:6379/0)
    redis_url: str = os.getenv("REDIS_URL", "")

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
