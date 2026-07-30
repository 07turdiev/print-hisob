"""`POST /api/ad-sync` uchun baza talab qilmaydigan testlar."""

from conftest import CAPTURED

FULL_PAYLOAD = {
    "mode": "full",
    "employees": [
        {
            "login": "jsmith",
            "fullName": "John Smith",
            "department": "Buxgalteriya",
            "position": "Bosh mutaxassis",
            "active": True,
        },
        {
            "login": "agoncalves",
            "fullName": "Ana Goncalves",
            "department": "",
            "position": "",
            "active": False,
        },
    ],
}


def test_ad_sync_full_mode_returns_counts(client):
    r = client.post("/api/ad-sync", json=FULL_PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "full"
    assert body["received"] == 2


def test_ad_sync_captures_upsert_params(client):
    client.post("/api/ad-sync", json=FULL_PAYLOAD)
    upsert_params = CAPTURED[0]
    assert upsert_params["login_m0"] == "jsmith"
    assert upsert_params["full_name_m0"] == "John Smith"
    assert upsert_params["department_m0"] == "Buxgalteriya"
    assert upsert_params["position_m0"] == "Bosh mutaxassis"
    assert upsert_params["is_active_m1"] is False


def test_ad_sync_empty_strings_become_null(client):
    client.post("/api/ad-sync", json=FULL_PAYLOAD)
    upsert_params = CAPTURED[0]
    assert upsert_params["department_m1"] is None
    assert upsert_params["position_m1"] is None


def test_ad_sync_full_mode_issues_deactivate_statement(client):
    client.post("/api/ad-sync", json=FULL_PAYLOAD)
    # 1-chi so'rov: upsert; 2-chi so'rov: ro'yxatda yo'qlarni nofaol qilish (full rejim).
    assert len(CAPTURED) == 2


def test_ad_sync_delta_mode_skips_deactivate_statement(client):
    payload = {"mode": "delta", "employees": FULL_PAYLOAD["employees"]}
    client.post("/api/ad-sync", json=payload)
    assert len(CAPTURED) == 1


def test_ad_sync_empty_employee_list_is_accepted(client):
    r = client.post("/api/ad-sync", json={"mode": "delta", "employees": []})
    assert r.status_code == 200
    body = r.json()
    assert body == {"mode": "delta", "received": 0, "upserted": 0, "deactivated": 0}
    assert CAPTURED == []


def test_ad_sync_full_mode_with_empty_list_still_deactivates(client):
    # Bo'sh "full" paket — AD'da hech kim qolmagan degani, barcha faollar
    # nofaol qilinishi kerak (WHERE bandisiz UPDATE).
    r = client.post("/api/ad-sync", json={"mode": "full", "employees": []})
    assert r.status_code == 200
    assert len(CAPTURED) == 1


def test_ad_sync_invalid_payload_rejected(client):
    r = client.post("/api/ad-sync", json={"mode": "weird", "employees": []})
    assert r.status_code == 422


def test_ad_sync_status_builds_without_error(client):
    r = client.get("/api/ad-sync/status")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "lastSyncedAt": None,
        "employeeCount": 0,
        "activeCount": 0,
        "minutesSinceSync": None,
        "isStale": False,
    }


def test_ad_sync_status_without_bearer_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/ad-sync/status")
    assert r.status_code == 401
