"""Basic tests for API and app startup."""
import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "ok"


def test_routes_list(client):
    r = client.get("/routes")
    assert r.status_code == 200
    data = r.get_json()
    assert "routes" in data
    assert "/health" in data["routes"]


def test_ask_requires_body(client):
    r = client.post("/ask", json={}, headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
