"""Pytest fixtures for Flask app."""
import os
import pytest


@pytest.fixture(scope="session")
def app_env():
    """Ensure minimal env so app can start without real API keys."""
    env = {
        "USE_STATIC": "0",  # Skip static files in tests
    }
    for k, v in env.items():
        os.environ[k] = v
    yield
    for k in env:
        os.environ.pop(k, None)


@pytest.fixture
def client(app_env):
    from app.main import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
