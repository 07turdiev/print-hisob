"""`GET /api/stats/*` uchun baza talab qilmaydigan testlar.

Haqiqiy bazasiz `FakeSession` har doim bo'sh natija qaytaradi, shuning uchun bu
yerda faqat SQL to'g'ri qurilishi, davr chegaralari va javob shakli tekshiriladi
(qiymatlarning aniqligi emas — bu integratsion testlar ishi).
"""

from app.config import settings

PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}

# Standart kvota qiymatlari sozlamadan olinadi — testlar `.env` yoki
# `Settings` dagi o'zgarishga bog'lanib qolmasligi uchun.
QUARTER_QUOTA = settings.default_quota_quarter
MONTH_QUOTA = settings.default_quota_month


def test_stats_summary_builds_without_error(client):
    r = client.get("/api/stats/summary", params=PERIOD)
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "periodType": "quarter",
        "year": 2026,
        "periodNo": 3,
        "totalPages": 0,
        "totalJobs": 0,
        "successRate": 0.0,
        "activePrinters": 0,
        "defaultQuota": QUARTER_QUOTA,
    }


def test_stats_summary_default_quota_for_month(client):
    r = client.get(
        "/api/stats/summary", params={"period_type": "month", "year": 2026, "period_no": 7}
    )
    assert r.status_code == 200
    assert r.json()["defaultQuota"] == MONTH_QUOTA


def test_stats_summary_default_quota_for_quarter(client):
    r = client.get("/api/stats/summary", params=PERIOD)
    assert r.status_code == 200
    assert r.json()["defaultQuota"] == QUARTER_QUOTA


def test_stats_employees_sql_uses_default_quota_for_quarter(client):
    from conftest import CAPTURED

    r = client.get("/api/stats/employees", params=PERIOD)
    assert r.status_code == 200
    assert any(QUARTER_QUOTA in params.values() for params in CAPTURED)


def test_stats_employees_sql_uses_default_quota_for_month(client):
    from conftest import CAPTURED

    r = client.get(
        "/api/stats/employees", params={"period_type": "month", "year": 2026, "period_no": 7}
    )
    assert r.status_code == 200
    assert any(MONTH_QUOTA in params.values() for params in CAPTURED)


def test_stats_departments_sql_uses_default_quota_for_quarter(client):
    from conftest import CAPTURED

    r = client.get("/api/stats/departments", params=PERIOD)
    assert r.status_code == 200
    assert any(QUARTER_QUOTA in params.values() for params in CAPTURED)


def test_stats_departments_sql_uses_default_quota_for_month(client):
    from conftest import CAPTURED

    r = client.get(
        "/api/stats/departments", params={"period_type": "month", "year": 2026, "period_no": 7}
    )
    assert r.status_code == 200
    assert any(MONTH_QUOTA in params.values() for params in CAPTURED)


def test_stats_employees_builds_without_error(client):
    r = client.get("/api/stats/employees", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_timeseries_builds_without_error(client):
    r = client.get("/api/stats/timeseries", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_top_builds_without_error(client):
    r = client.get("/api/stats/top", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == {"printers": [], "computers": [], "departments": []}


def test_stats_failures_builds_without_error(client):
    r = client.get("/api/stats/failures", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_month_period_builds_without_error(client):
    r = client.get("/api/stats/summary", params={"period_type": "month", "year": 2026, "period_no": 7})
    assert r.status_code == 200


def test_stats_invalid_quarter_period_no_rejected(client):
    r = client.get(
        "/api/stats/summary", params={"period_type": "quarter", "year": 2026, "period_no": 5}
    )
    assert r.status_code == 422


def test_stats_invalid_month_period_no_rejected(client):
    r = client.get(
        "/api/stats/employees", params={"period_type": "month", "year": 2026, "period_no": 0}
    )
    assert r.status_code == 422


def test_stats_missing_query_params_rejected(client):
    r = client.get("/api/stats/summary")
    assert r.status_code == 422
