"""`POST /api/print-quotas` uchun baza talab qilmaydigan testlar.

`FakeSession` har doim bo'sh natija qaytaradi, shuning uchun bu yerda javob
**shakli** va hujjatdagi qoidalarga muvofiqligi tekshiriladi (aniq raqamlar
emas — bu integratsion testlar ishi).
"""

from datetime import datetime, timezone

import pytest

from app.config import settings
from app.logins import normalize_login
from app.periods import current_period, period_key

BODY = {
    "computer": "LAPTOP-JANE",
    "periodKey": "2026-Q1",
    "timestamp": "2026-09-08T09:15:00Z",
    "users": [{"user": "jane", "pagesUsedHere": 42, "pagesUsed": 137, "limit": 1000}],
}


def _expected_key() -> str:
    """Server javobida bo'lishi kerak bo'lgan joriy davr identifikatori."""
    period = current_period("quarter")
    return period_key("quarter", period.year, period.period_no)


# ---------------------------------------------------------------------------
# Login normallashtirish (hujjatdagi "Uch nozik qoida", 3-band)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("jane", "jane"),
        ("Jane", "jane"),
        ("ACME\\Jane", "jane"),
        ("MADANIYAT\\E.Turdiyev", "e.turdiyev"),
        ("  MADANIYAT\\e.turdiyev  ", "e.turdiyev"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_login(raw, expected):
    assert normalize_login(raw) == expected


# ---------------------------------------------------------------------------
# Davr identifikatori
# ---------------------------------------------------------------------------


def test_period_key_format():
    assert period_key("quarter", 2026, 3) == "2026-Q3"
    assert period_key("month", 2026, 9) == "2026-09"
    # Bir xonali oy nol bilan to'ldiriladi — satr barqaror uzunlikda bo'lsin.
    assert period_key("month", 2026, 7) == "2026-07"


def test_current_period_matches_calendar():
    now = datetime.now(timezone.utc)
    period = current_period("quarter")
    assert period.year == now.year
    assert period.period_no == (now.month - 1) // 3 + 1
    assert period.start <= now < period.end


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


def test_sync_returns_period_key_and_default_limit(client):
    r = client.post("/api/print-quotas", json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["periodKey"] == _expected_key()
    assert body["defaultLimit"] == settings.default_quota_quarter


def test_sync_ignores_period_key_sent_by_agent(client):
    """Davrni server belgilaydi — agent yuborgan eski `periodKey` javobga ta'sir qilmaydi."""
    r = client.post("/api/print-quotas", json={**BODY, "periodKey": "2019-Q1"})
    assert r.status_code == 200
    assert r.json()["periodKey"] == _expected_key()


def test_sync_echoes_requested_user(client):
    """So'ralgan foydalanuvchi javobda bo'lishi kerak — agent uni keshlab qo'yadi."""
    r = client.post("/api/print-quotas", json=BODY)
    assert r.status_code == 200
    users = r.json()["users"]
    assert [u["user"] for u in users] == ["jane"]
    # Kvota belgilanmagan (bazada qator yo'q) -> `null`, ya'ni agent `defaultLimit`ga tushadi.
    # Bu `-1` (aniq cheklovsiz) bilan bir xil emas.
    assert users[0]["limit"] is None
    assert users[0]["used"] == 0


def test_sync_keeps_user_name_as_sent(client):
    r = client.post(
        "/api/print-quotas",
        json={**BODY, "users": [{"user": "MADANIYAT\\E.Turdiyev", "pagesUsedHere": 1}]},
    )
    assert r.status_code == 200
    assert r.json()["users"][0]["user"] == "MADANIYAT\\E.Turdiyev"


def test_sync_accepts_empty_user_list(client):
    """Hech kim chop etmagan mashina ham limitlarni so'raydi (kesh yangilash uchun)."""
    r = client.post(
        "/api/print-quotas",
        json={"computer": "PC-EMPTY", "timestamp": "2026-09-08T09:15:00Z", "users": []},
    )
    assert r.status_code == 200
    assert r.json()["users"] == []
    assert r.json()["defaultLimit"] == settings.default_quota_quarter


def test_sync_accepts_missing_period_key(client):
    """Agentning birinchi so'rovida `periodKey` bo'lmaydi."""
    payload = {k: v for k, v in BODY.items() if k != "periodKey"}
    r = client.post("/api/print-quotas", json=payload)
    assert r.status_code == 200


def test_sync_accepts_negative_limit_from_agent(client):
    """`-1` (cheklovsiz) yaroqli qiymat — validatsiya uni rad etmasligi kerak."""
    r = client.post(
        "/api/print-quotas",
        json={**BODY, "users": [{"user": "ceo", "pagesUsedHere": 0, "limit": -1}]},
    )
    assert r.status_code == 200


def test_sync_rejects_missing_timestamp(client):
    payload = {k: v for k, v in BODY.items() if k != "timestamp"}
    r = client.post("/api/print-quotas", json=payload)
    assert r.status_code == 422


def test_sync_writes_agent_state(client):
    """Agent hisoboti bazaga yozilishi kerak (`agent_quota_state` upsert)."""
    from conftest import CAPTURED

    r = client.post("/api/print-quotas", json=BODY)
    assert r.status_code == 200
    # Normallashtirilgan login va kompyuter nomi bind-parametrlarda ko'rinadi.
    assert any("jane" in params.values() for params in CAPTURED)
    assert any("LAPTOP-JANE" in params.values() for params in CAPTURED)
    # Agent qo'llayotgan limit ham saqlanadi.
    assert any(1000 in params.values() for params in CAPTURED)


def test_sync_requires_api_key_when_configured(monkeypatch):
    """API kalit sozlangan bo'lsa, kalitsiz so'rov 401 olishi kerak.

    Hujjatdagi tavsiya: noto'g'ri kalitda `2xx` qaytarmaslik — aks holda agent
    ma'lumotni yuborilgan deb hisoblab, buferdan o'chirib yuboradi.
    """
    from fastapi.testclient import TestClient

    from app.db import get_session
    from app.main import app
    from conftest import _fake_session

    monkeypatch.setattr(settings, "api_key", "maxfiy-kalit")
    app.dependency_overrides[get_session] = _fake_session
    try:
        with TestClient(app) as c:
            assert c.post("/api/print-quotas", json=BODY).status_code == 401
            # Agent `X-Api-Key` yozadi — HTTP sarlavhalari registrga sezgir emas.
            ok = c.post("/api/print-quotas", json=BODY, headers={"X-Api-Key": "maxfiy-kalit"})
            assert ok.status_code == 200
    finally:
        app.dependency_overrides.clear()
