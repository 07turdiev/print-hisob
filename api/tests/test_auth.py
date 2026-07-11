"""`POST /api/auth/login` va `require_user` (Bearer/JWT) uchun baza talab qilmaydigan testlar."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_login_with_correct_credentials_returns_token(client):
    r = client.post(
        "/api/auth/login",
        json={"username": settings.auth_username, "password": settings.auth_password},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tokenType"] == "bearer"
    assert isinstance(body["accessToken"], str) and body["accessToken"]
    assert body["expiresIn"] == settings.jwt_expire_minutes * 60


def test_login_with_wrong_password_rejected(client):
    r = client.post(
        "/api/auth/login",
        json={"username": settings.auth_username, "password": "notug'ri-parol"},
    )
    assert r.status_code == 401


def test_login_with_wrong_username_rejected(client):
    r = client.post(
        "/api/auth/login",
        json={"username": "boshqa-user", "password": settings.auth_password},
    )
    assert r.status_code == 401


def test_login_missing_body_rejected(client):
    r = client.post("/api/auth/login", json={"username": "admin"})
    assert r.status_code == 422


def test_protected_endpoint_without_token_rejected():
    # `client` fixture'i Bearer tokenni avtomatik qo'shadi — bu yerda ataylab
    # xom `TestClient` ishlatiladi, sarlavhasiz so'rov yuborish uchun.
    with TestClient(app) as c:
        r = c.get("/api/quotas")
    assert r.status_code == 401


def test_protected_endpoint_with_invalid_token_rejected():
    with TestClient(app) as c:
        r = c.get("/api/quotas", headers={"Authorization": "Bearer yaroqsiz-token"})
    assert r.status_code == 401


def test_protected_endpoint_with_valid_token_allowed(client):
    r = client.get("/api/quotas")
    assert r.status_code == 200


def test_ingest_endpoint_still_uses_api_key_not_bearer(client):
    # POST /api/print-jobs — agentlar uchun, Bearer talab qilmaydi (API_KEY bo'sh
    # bo'lgani uchun sarlavhasiz ham ishlashi kerak).
    with TestClient(app) as c:
        r = c.post("/api/print-jobs", json={"computer": "X", "jobs": []})
    assert r.status_code == 201
