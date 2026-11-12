"""Portal API'si kaliti va davr parametrlari (bazasiz)."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

URL = "/api/portal/v1/employees/ali/printing"


def test_portal_is_closed_until_a_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", "")
    with TestClient(app) as c:
        r = c.get(URL, headers={"X-Portal-Key": "nimadir"})
    assert r.status_code == 503


def test_portal_rejects_missing_and_wrong_key(monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", "togri-kalit")
    with TestClient(app) as c:
        assert c.get(URL).status_code == 401
        assert c.get(URL, headers={"X-Portal-Key": "notogri"}).status_code == 401


def test_dashboard_token_and_agent_key_do_not_open_the_portal(client, monkeypatch):
    """`client` dashboard token'i bilan keladi, u portal kaliti o'rnini bosmaydi."""
    monkeypatch.setattr(settings, "portal_api_key", "togri-kalit")
    monkeypatch.setattr(settings, "api_key", "agent-kaliti")
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"X-API-Key": "agent-kaliti"}).status_code == 401


def test_year_without_period_no_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", "togri-kalit")
    r = client.get(URL, params={"year": 2026}, headers={"X-Portal-Key": "togri-kalit"})
    assert r.status_code == 422


def test_bad_period_no_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", "togri-kalit")
    r = client.get(
        URL,
        params={"period_type": "quarter", "year": 2026, "period_no": 5},
        headers={"X-Portal-Key": "togri-kalit"},
    )
    assert r.status_code == 422
