"""`/api/quotas` (GET/PUT) uchun baza talab qilmaydigan testlar."""

from conftest import CAPTURED

SINGLE_QUOTA = {
    "login": "jsmith",
    "periodType": "quarter",
    "year": 2026,
    "periodNo": 3,
    "allocatedPages": 1500,
}

QUOTA_LIST = [
    SINGLE_QUOTA,
    {
        "login": "agoncalves",
        "periodType": "month",
        "year": 2026,
        "periodNo": 7,
        "allocatedPages": 500,
    },
]


def test_put_single_quota_is_accepted(client):
    r = client.put("/api/quotas", json=SINGLE_QUOTA)
    assert r.status_code == 200
    assert r.json() == []  # bazasiz muhitda RETURNING qator qaytarmaydi


def test_put_single_quota_captures_upsert_params(client):
    client.put("/api/quotas", json=SINGLE_QUOTA)
    params = CAPTURED[0]
    assert params["login_m0"] == "jsmith"
    assert params["period_type_m0"] == "quarter"
    assert params["year_m0"] == 2026
    assert params["period_no_m0"] == 3
    assert params["allocated_pages_m0"] == 1500


def test_put_list_of_quotas_is_accepted(client):
    r = client.put("/api/quotas", json=QUOTA_LIST)
    assert r.status_code == 200
    params = CAPTURED[0]
    assert params["login_m0"] == "jsmith"
    assert params["login_m1"] == "agoncalves"
    assert params["period_type_m1"] == "month"


def test_put_empty_list_is_accepted(client):
    r = client.put("/api/quotas", json=[])
    assert r.status_code == 200
    assert r.json() == []
    assert CAPTURED == []


def test_month_period_no_out_of_range_rejected(client):
    bad = dict(SINGLE_QUOTA) | {"periodType": "month", "periodNo": 13}
    r = client.put("/api/quotas", json=bad)
    assert r.status_code == 422


def test_quarter_period_no_out_of_range_rejected(client):
    bad = dict(SINGLE_QUOTA) | {"periodType": "quarter", "periodNo": 5}
    r = client.put("/api/quotas", json=bad)
    assert r.status_code == 422


def test_period_no_zero_rejected(client):
    bad = dict(SINGLE_QUOTA) | {"periodType": "quarter", "periodNo": 0}
    r = client.put("/api/quotas", json=bad)
    assert r.status_code == 422


def test_invalid_period_type_rejected(client):
    bad = dict(SINGLE_QUOTA) | {"periodType": "week"}
    r = client.put("/api/quotas", json=bad)
    assert r.status_code == 422


def test_list_quotas_builds_without_error(client):
    r = client.get("/api/quotas")
    assert r.status_code == 200
    assert r.json() == []


def test_list_quotas_accepts_filters(client):
    r = client.get(
        "/api/quotas",
        params={"period_type": "quarter", "year": 2026, "period_no": 3, "login": "jsmith"},
    )
    assert r.status_code == 200
