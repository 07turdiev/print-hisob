"""`/api/user-overrides` — bloklash va biriktirish uchun bazasiz testlar.

`FakeSession` har doim bo'sh natija qaytaradi, shuning uchun bu yerda javob
shakli va **tekshiruv qoidalari** sinaladi. Qoidalar muvaffaqiyatli bajarilishi
(haqiqiy biriktirish) integratsion sinovda tekshiriladi.
"""

import pytest

BLOCK = {"blocked": True, "blockedReason": "Shaxsiy hujjatlarni chop etgani uchun"}


# ---------------------------------------------------------------------------
# Bloklash
# ---------------------------------------------------------------------------


def test_block_returns_saved_state(client):
    r = client.put("/api/user-overrides/b.soliyev", json=BLOCK)
    assert r.status_code == 200
    body = r.json()
    assert body["login"] == "b.soliyev"
    assert body["blocked"] is True
    assert body["blockedReason"] == BLOCK["blockedReason"]
    # Kim bloklagani tokendagi foydalanuvchidan olinadi.
    assert body["blockedBy"] == "admin"
    assert body["blockedAt"] is not None


def test_unblock_clears_reason_and_author(client):
    """Blokdan chiqarilganda sabab va muallif qolib ketmasligi kerak."""
    r = client.put("/api/user-overrides/b.soliyev", json={"blocked": False})
    assert r.status_code == 200
    body = r.json()
    assert body["blocked"] is False
    assert body["blockedReason"] is None
    assert body["blockedBy"] is None
    assert body["blockedAt"] is None


def test_login_is_normalized(client):
    """`MADANIYAT\\B.Soliyev` va `b.soliyev` — bitta odam."""
    r = client.put("/api/user-overrides/MADANIYAT%5CB.Soliyev", json={"blocked": True})
    assert r.status_code == 200
    assert r.json()["login"] == "b.soliyev"


def test_empty_payload_rejected(client):
    """Hech narsa yuborilmagan so'rov jimgina 200 qaytarmasligi kerak."""
    r = client.put("/api/user-overrides/b.soliyev", json={})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Biriktirish qoidalari
# ---------------------------------------------------------------------------


def test_cannot_link_to_self(client):
    r = client.put("/api/user-overrides/a.karimov", json={"chargeToLogin": "a.karimov"})
    assert r.status_code == 400
    assert "o'ziga" in r.json()["detail"]


def test_cannot_link_to_self_ignoring_case_and_domain(client):
    """Normallashtirishdan keyin bir xil bo'lsa ham o'ziga biriktirib bo'lmaydi."""
    r = client.put(
        "/api/user-overrides/a.karimov", json={"chargeToLogin": "MADANIYAT\\A.Karimov"}
    )
    assert r.status_code == 400


def test_link_to_unknown_employee_rejected(client):
    """Xodimlar ro'yxatida yo'q loginga biriktirib bo'lmaydi (imlo xatosi himoyasi)."""
    r = client.put("/api/user-overrides/b.soliyev", json={"chargeToLogin": "yoq.odam"})
    assert r.status_code == 400
    assert "topilmadi" in r.json()["detail"]


def test_unlink_needs_no_employee_check(client):
    """Biriktirishni bekor qilishda tekshiruv o'tkazilmaydi — `null` har doim yaroqli."""
    r = client.put("/api/user-overrides/b.soliyev", json={"chargeToLogin": None})
    assert r.status_code == 200
    assert r.json()["chargeToLogin"] is None


# ---------------------------------------------------------------------------
# Qisman yangilash
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload,touched,untouched",
    [
        ({"blocked": True}, "blocked", "charge_to_login"),
        ({"chargeToLogin": None}, "charge_to_login", "blocked"),
    ],
)
def test_only_sent_fields_are_updated(client, payload, touched, untouched):
    """Yuborilmagan maydon mavjud qatorda o'zgarmasligi kerak.

    Tekshiruv aynan `ON CONFLICT DO UPDATE SET` qismiga qaratilgan: INSERT
    parametrlarida SQLAlchemy ustun standartlarini ham qo'shadi (yangi qator
    uchun to'g'ri), lekin mavjud qator faqat SET dagi ustunlar bo'yicha
    yangilanadi. Aks holda faqat bloklaganda biriktirish ham tozalanib ketardi.
    """
    from conftest import CAPTURED_SQL

    CAPTURED_SQL.clear()
    r = client.put("/api/user-overrides/b.soliyev", json=payload)
    assert r.status_code == 200

    upserts = [sql for sql in CAPTURED_SQL if "ON CONFLICT" in sql]
    assert upserts, "upsert topilmadi"
    # `RETURNING` barcha ustun nomlarini sanaydi — uni kesib tashlaymiz,
    # aks holda tekshiruv har doim "tegilgan" deb topadi.
    set_clause = upserts[-1].split("DO UPDATE SET", 1)[1].split(" RETURNING", 1)[0]
    assert touched in set_clause
    assert untouched not in set_clause


# ---------------------------------------------------------------------------
# Ro'yxat va autentifikatsiya
# ---------------------------------------------------------------------------


def test_list_returns_array(client):
    r = client.get("/api/user-overrides")
    assert r.status_code == 200
    assert r.json() == []


def test_requires_authentication():
    from fastapi.testclient import TestClient

    from app.db import get_session
    from app.main import app
    from conftest import _fake_session

    app.dependency_overrides[get_session] = _fake_session
    try:
        with TestClient(app) as c:
            assert c.get("/api/user-overrides").status_code == 401
            assert c.put("/api/user-overrides/x", json={"blocked": True}).status_code == 401
    finally:
        app.dependency_overrides.clear()
