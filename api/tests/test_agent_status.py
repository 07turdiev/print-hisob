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

FULL_PAYLOAD = {
    "computer": "DESKTOP-20DJFSC",
    "username": "jdoe",
    "version": "1.4.11",
    "working": True,
    "detail": "",
    "bootTimeUtc": "2026-07-20T05:12:44+00:00",
    "uptimeSeconds": 274320,
    "agentUptimeSeconds": 63,
    "timestamp": "2026-07-23T09:38:47+00:00",
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


def test_agent_status_new_fields_captured(client):
    r = client.post("/api/agent-status", json=FULL_PAYLOAD)
    assert r.status_code == 200
    params = CAPTURED[-1]
    assert params["boot_time_utc"].isoformat() == "2026-07-20T05:12:44+00:00"
    assert params["uptime_seconds"] == 274320
    assert params["agent_uptime_seconds"] == 63


def test_agent_status_without_new_fields_defaults_to_null(client):
    r = client.post("/api/agent-status", json=PAYLOAD)
    assert r.status_code == 200
    params = CAPTURED[-1]
    assert params["boot_time_utc"] is None
    assert params["uptime_seconds"] is None
    assert params["agent_uptime_seconds"] is None


def test_agent_status_negative_uptime_rejected(client):
    job = dict(FULL_PAYLOAD) | {"uptimeSeconds": -1}
    r = client.post("/api/agent-status", json=job)
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
    assert r.json() == {
        "total": 0,
        "working": 0,
        "notWorking": 0,
        "stale": 0,
        "recentlyRestarted": 0,
    }


def test_agents_summary_without_bearer_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/agents/summary")
    assert r.status_code == 401
