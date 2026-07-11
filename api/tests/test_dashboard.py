"""Yangi dashboard endpointlari (`/api/employees`, `/api/stats/printers`,
`/api/stats/departments`) va bo'lim filtrlari uchun baza talab
qilmaydigan testlar. Barchasi `require_user` (Bearer) bilan himoyalangan.
"""

PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}


def test_list_employees_builds_without_error(client):
    r = client.get("/api/employees")
    assert r.status_code == 200
    assert r.json() == []


def test_list_employees_accepts_filters(client):
    r = client.get(
        "/api/employees",
        params={
            "department": "Buxgalteriya",
            "is_active": True,
            "q": "jsmith",
            "limit": 50,
            "offset": 0,
        },
    )
    assert r.status_code == 200


def test_stats_printers_builds_without_error(client):
    r = client.get("/api/stats/printers", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_departments_builds_without_error(client):
    r = client.get("/api/stats/departments", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_print_jobs_returns_total_count_header(client):
    r = client.get("/api/print-jobs")
    assert r.status_code == 200
    assert "X-Total-Count" in r.headers
    assert r.headers["X-Total-Count"] == "0"


def test_print_jobs_without_bearer_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/print-jobs")
    assert r.status_code == 401


def test_stats_summary_accepts_department_filter(client):
    r = client.get("/api/stats/summary", params=PERIOD | {"department": "Buxgalteriya"})
    assert r.status_code == 200


def test_stats_timeseries_accepts_department_filter(client):
    r = client.get("/api/stats/timeseries", params=PERIOD | {"department": "Buxgalteriya"})
    assert r.status_code == 200
    assert r.json() == []


def test_stats_top_accepts_department_filter(client):
    r = client.get("/api/stats/top", params=PERIOD | {"department": "Buxgalteriya"})
    assert r.status_code == 200
    assert r.json() == {"printers": [], "computers": [], "departments": []}


def test_stats_failures_accepts_department_filter(client):
    r = client.get("/api/stats/failures", params=PERIOD | {"department": "Buxgalteriya"})
    assert r.status_code == 200
    assert r.json() == []


def test_stats_employees_accepts_department_filter(client):
    r = client.get("/api/stats/employees", params=PERIOD | {"department": "Buxgalteriya"})
    assert r.status_code == 200
    assert r.json() == []


def test_stats_summary_without_filters_still_works(client):
    # Filtrsiz eski xatti-harakat o'zgarmasligini tekshiradi.
    r = client.get("/api/stats/summary", params=PERIOD)
    assert r.status_code == 200


def test_stats_period_no_validation_still_enforced(client):
    r = client.get(
        "/api/stats/summary", params={"period_type": "quarter", "year": 2026, "period_no": 5}
    )
    assert r.status_code == 422
