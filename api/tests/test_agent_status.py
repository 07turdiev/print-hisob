"""`POST /api/agent-status`, `GET /api/agents`, `GET /api/agents/summary` uchun
baza talab qilmaydigan testlar (`conftest.FakeSession` orqali)."""

from conftest import CAPTURED

from app.config import settings

PAYLOAD = {
    "computer": "DESKTOP-20DJFSC",
    "username": "Sarvar Mamatqulov",
    "version": "1.4.6.0",
    "working": True,
    "detail": "",
    "timestamp": "2026-07-13T10:22:31Z",
}


def test_agent_status_ingest_returns_ok(client):
    r = client.post("/api/agent-status", json=PAYLOAD)
    assert r.status_code == 200
    assert r.json() == {"computer": "DESKTOP-20DJFSC", "status": "ok"}


def test_agent_status_captures_upsert_params(client):
    client.post("/api/agent-status", json=PAYLOAD)
    params = CAPTURED[-1]
    assert params["computer"] == "DESKTOP-20DJFSC"
    assert params["username"] == "Sarvar Mamatqulov"
    assert params["version"] == "1.4.6.0"
    assert params["working"] is True


def test_agent_status_empty_detail_becomes_null(client):
    client.post("/api/agent-status", json=PAYLOAD)
    params = CAPTURED[-1]
    assert params["detail"] is None


def test_agent_status_plain_z_timestamp_parses_as_utc(client):
    client.post("/api/agent-status", json=PAYLOAD)
    params = CAPTURED[-1]
    assert params["reported_at"].isoformat() == "2026-07-13T10:22:31+00:00"


def test_agent_status_working_false_with_detail_message(client):
    job = dict(PAYLOAD) | {"working": False, "detail": "Spooler ishlamayapti"}
    client.post("/api/agent-status", json=job)
    params = CAPTURED[-1]
    assert params["working"] is False
    assert params["detail"] == "Spooler ishlamayapti"


def test_agent_status_requires_api_key_when_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "sekret-kalit")
    r = client.post("/api/agent-status", json=PAYLOAD)
    assert r.status_code == 401

    r = client.post(
        "/api/agent-status", json=PAYLOAD, headers={"X-API-Key": "sekret-kalit"}
    )
    assert r.status_code == 200


def test_agent_status_invalid_payload_rejected(client):
    r = client.post("/api/agent-status", json={"computer": "X"})
    assert r.status_code == 422


def test_list_agents_builds_without_error(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    assert r.json() == []


def test_list_agents_accepts_filters(client):
    r = client.get(
        "/api/agents",
        params={"working": False, "stale": True, "q": "DESKTOP"},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_list_agents_without_bearer_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/agents")
    assert r.status_code == 401


def test_agents_summary_builds_without_error(client):
    r = client.get("/api/agents/summary")
    assert r.status_code == 200
    assert r.json() == {"total": 0, "working": 0, "notWorking": 0, "stale": 0}


def test_agents_summary_without_bearer_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/agents/summary")
    assert r.status_code == 401
