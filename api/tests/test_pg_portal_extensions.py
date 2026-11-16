"""Portal API kengaytmasi (haqiqiy Postgres): yangi maydonlar, tarix, davrlar, bo'limlar.

Asosiy talab: portaldagi har bir raqam dashboard va `/printing` dagi raqam bilan
bir xil chiqishi, bo'limlar kesimida biriktirish ikki marta sanalmasligi.
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from sqlalchemy import event

from app.config import settings
from app.periods import current_period, previous_period
from test_pg_agent_contract import job, net_timestamp, send_jobs
from test_pg_report_rules import CANCELLED, link

NOW = datetime.now(timezone.utc)
KEY = "portal-sinov-kaliti"
HEADERS = {"X-Portal-Key": KEY}
QUARTER = current_period("quarter")
PREVIOUS = previous_period(QUARTER)
PERIOD = {"period_type": "quarter", "year": QUARTER.year, "period_no": QUARTER.period_no}
XALQARO = "Xalqaro aloqalar bo'limi"


@pytest.fixture(autouse=True)
def portal_key(monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", KEY)


def person(login: str, department: str | None = "IT", active: bool = True) -> dict:
    return {
        "login": login,
        "fullName": login.title(),
        "department": department,
        "position": "Xodim",
        "active": active,
    }


def sync(pg, *people) -> None:
    pg.client.post("/api/ad-sync", json={"mode": "full", "employees": list(people)}).raise_for_status()


def at(i: int, moment: datetime, **extra) -> dict:
    return job(i, timestamp=net_timestamp(moment), **extra)


def portal(pg, path: str, **params):
    r = pg.client.get(f"/api/portal/v1{path}", params=params, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def set_quota(pg, login: str, period, pages: int) -> None:
    pg.client.put(
        "/api/quotas",
        json={
            "login": login,
            "periodType": period.period_type,
            "year": period.year,
            "periodNo": period.period_no,
            "allocatedPages": pages,
        },
    ).raise_for_status()


# ---------------------------------------------------------------------------
# /printing: yangi maydonlar
# ---------------------------------------------------------------------------


def test_linked_logins_with_zero_usage_unknown_and_inactive(pg):
    sync(pg, person("egasi"), person("amaliyotchi"), person("ketgan", active=False))
    send_jobs(
        pg,
        job(1, user="amaliyotchi", pages=7),
        job(2, user="begona", pages=3),
        job(3, user="amaliyotchi", pages=0, success=False, reason=CANCELLED),
    )
    for login in ("amaliyotchi", "begona", "ketgan", "bekor"):
        link(pg, login, "egasi")

    quota = portal(pg, "/employees/egasi/printing")["quota"]
    assert quota["linked"] == [
        {"login": "amaliyotchi", "fullName": "Amaliyotchi", "status": "active", "pages": 7, "jobs": 1},
        {"login": "begona", "fullName": None, "status": "unknown", "pages": 3, "jobs": 1},
        {"login": "bekor", "fullName": None, "status": "unknown", "pages": 0, "jobs": 0},
        {"login": "ketgan", "fullName": "Ketgan", "status": "inactive", "pages": 0, "jobs": 0},
    ]
    assert sum(item["pages"] for item in quota["linked"]) == quota["usedFromLinked"] == 10
    # Eski maydonlar avvalgidek.
    assert quota["linkedLogins"] == ["amaliyotchi", "begona", "bekor", "ketgan"]
    assert quota["chargedToEmployee"] is None


def test_charged_to_employee_and_allocated_source(pg):
    sync(pg, person("egasi"), person("amaliyotchi"))
    link(pg, "amaliyotchi", "egasi")
    set_quota(pg, "egasi", QUARTER, 40)

    intern = portal(pg, "/employees/amaliyotchi/printing")["quota"]
    assert intern["chargedTo"] == "egasi"
    assert intern["chargedToEmployee"] == {"login": "egasi", "fullName": "Egasi", "status": "active"}
    assert (intern["allocatedSource"], intern["isDefault"]) == ("default", True)

    owner = portal(pg, "/employees/egasi/printing")["quota"]
    assert (owner["allocatedSource"], owner["isDefault"], owner["allocated"]) == ("explicit", False, 40)


def test_period_is_current(pg):
    sync(pg, person("ali"))
    assert portal(pg, "/employees/ali/printing")["period"]["isCurrent"] is True
    previous = portal(
        pg,
        "/employees/ali/printing",
        period_type="quarter",
        year=PREVIOUS.year,
        period_no=PREVIOUS.period_no,
    )
    assert previous["period"]["isCurrent"] is False


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------


def test_history_matches_printing_for_every_period(pg):
    sync(pg, person("egasi"), person("amaliyotchi"))
    send_jobs(
        pg,
        # Davr chegarasi: birinchi ish oldingi chorakka, ikkinchisi joriysiga tushadi.
        at(1, QUARTER.start - timedelta(seconds=1), user="egasi", pages=5),
        at(2, QUARTER.start, user="egasi", pages=2),
        at(3, PREVIOUS.start + timedelta(days=3), user="amaliyotchi", pages=4),
        at(4, PREVIOUS.start + timedelta(days=4), user="egasi", printer="Microsoft Print to PDF", printerMac="", printerIp="", pages=9),
        job(5, user="egasi", pages=1),
    )
    link(pg, "amaliyotchi", "egasi")
    set_quota(pg, "egasi", PREVIOUS, 8)

    items = portal(pg, "/employees/egasi/history", period_type="quarter", count=3)
    assert [i["period"]["isCurrent"] for i in items] == [True, False, False]
    assert [(i["period"]["year"], i["period"]["periodNo"]) for i in items[:2]] == [
        (QUARTER.year, QUARTER.period_no),
        (PREVIOUS.year, PREVIOUS.period_no),
    ]

    fields = ["allocated", "used", "usedFromLinked", "usedTotal", "remaining", "percent", "overLimit", "isDefault"]
    for item in items:
        period = item["period"]
        quota = portal(
            pg,
            "/employees/egasi/printing",
            period_type=period["periodType"],
            year=period["year"],
            period_no=period["periodNo"],
        )["quota"]
        assert {f: item[f] for f in fields} == {f: quota[f] for f in fields}, period["label"]

    current, previous = items[0], items[1]
    assert (current["used"], current["usedFromLinked"]) == (3, 0)
    assert (previous["used"], previous["usedFromLinked"], previous["allocated"]) == (5, 4, 8)
    assert (previous["overLimit"], previous["isDefault"]) == (True, False)


def test_history_query_count_does_not_grow_with_periods(pg):
    sync(pg, person("ali"))
    send_jobs(pg, job(1, user="ali"))
    statements: list[str] = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(pg.engine.sync_engine, "before_cursor_execute", record)
    try:
        counts = []
        for count in (1, 12):
            statements.clear()
            portal(pg, "/employees/ali/history", count=count)
            counts.append(len(statements))
    finally:
        event.remove(pg.engine.sync_engine, "before_cursor_execute", record)
    assert counts[0] > 0 and counts[0] == counts[1], counts


def test_history_months_and_count_limits(pg):
    sync(pg, person("ali"))
    items = portal(pg, "/employees/ali/history", period_type="month", count=12)
    assert len(items) == 12
    assert items[0]["period"]["periodType"] == "month"
    assert all(i["allocated"] == settings.default_quota_month for i in items)

    for bad in (0, 13):
        r = pg.client.get("/api/portal/v1/employees/ali/history", params={"count": bad}, headers=HEADERS)
        assert r.status_code == 422
    r = pg.client.get("/api/portal/v1/employees/hech.kim/history", headers=HEADERS)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /periods
# ---------------------------------------------------------------------------


def test_periods_bounds(pg):
    empty = portal(pg, "/periods")
    assert empty["defaultPeriodType"] == "quarter"
    assert empty["earliest"] is None
    assert empty["current"]["quarter"]["isCurrent"] is True
    assert empty["current"]["month"]["periodType"] == "month"

    first = PREVIOUS.start + timedelta(days=40)
    send_jobs(
        pg,
        # PDF ish hisobga kirmaydi, chegarani surmaydi.
        at(1, PREVIOUS.start, printer="Microsoft Print to PDF", printerMac="", printerIp=""),
        at(2, first),
        job(3),
    )
    earliest = portal(pg, "/periods")["earliest"]
    assert (earliest["quarter"]["year"], earliest["quarter"]["periodNo"]) == (PREVIOUS.year, PREVIOUS.period_no)
    assert (earliest["month"]["year"], earliest["month"]["periodNo"]) == (first.year, first.month)


# ---------------------------------------------------------------------------
# /departments
# ---------------------------------------------------------------------------


def _org(pg):
    """Ikki bo'lim, biriktirish bo'limlar orasida, ketgan xodim va AD'da yo'q login."""
    sync(
        pg,
        person("rahbar", XALQARO),
        person("bekorchi", XALQARO),
        person("amaliyotchi", "IT"),
        person("ketgan", "IT", active=False),
        person("bolimsiz", None),
    )
    send_jobs(
        pg,
        job(1, user="rahbar", pages=10),
        job(2, user="amaliyotchi", pages=7),
        job(3, user="ketgan", pages=4),
        job(4, user="begona", pages=6),
        job(5, user="bolimsiz", pages=2),
        job(6, user="rahbar", pages=0, success=False, reason=CANCELLED),
    )
    link(pg, "amaliyotchi", "rahbar")
    set_quota(pg, "rahbar", QUARTER, 15)


def test_departments_add_up_to_the_dashboard_total(pg):
    _org(pg)
    body = portal(pg, "/departments", **PERIOD)
    rows = {r["department"]: r for r in body["departments"]}

    summary = pg.client.get("/api/stats/summary", params=PERIOD).json()
    assert sum(r["used"] for r in body["departments"]) == body["totalUsed"] == summary["totalPages"] == 29
    assert sum(r["jobs"] for r in body["departments"]) == body["totalJobs"] == summary["totalJobs"]

    # Biriktirish ikki marta sanalmaydi: amaliyotchining 7 varag'i faqat IT da.
    assert rows[XALQARO]["used"] == 10
    assert rows["IT"]["used"] == 11
    # Normadan oshgan xodim darajasida: rahbar 10 + 7 = 17 > 15.
    assert rows[XALQARO]["overLimitCount"] == 1
    assert rows["IT"]["overLimitCount"] == 0
    # Ketgan xodim soni va normaga kirmaydi, sarfi kiradi.
    assert rows["IT"]["employeeCount"] == 1
    assert rows["IT"]["allocated"] == settings.default_quota_quarter

    unassigned = body["departments"][-1]
    assert unassigned == {
        "department": None,
        "name": "Bo'limi aniqlanmagan",
        "employeeCount": None,
        "allocated": None,
        "used": 8,
        "jobs": 2,
        "percent": None,
        "overLimitCount": None,
    }

    dashboard = {d["name"]: d["pages"] for d in pg.client.get("/api/stats/departments", params=PERIOD).json()}
    assert {k: r["used"] for k, r in rows.items() if k} == dashboard


def test_department_employees_with_apostrophe_and_no_documents(pg):
    _org(pg)
    body = portal(pg, f"/departments/{quote(XALQARO, safe='')}/employees", **PERIOD)
    assert body["department"] == XALQARO
    people = {e["login"]: e for e in body["employees"]}
    assert set(people) == {"rahbar", "bekorchi"}
    assert (people["rahbar"]["used"], people["rahbar"]["usedFromLinked"], people["rahbar"]["usedTotal"]) == (10, 7, 17)
    assert (people["rahbar"]["overLimit"], people["rahbar"]["percent"]) == (True, 113.3)
    assert (people["bekorchi"]["used"], people["bekorchi"]["allocated"]) == (0, settings.default_quota_quarter)

    allowed = {"login", "fullName", "status", "allocated", "used", "usedFromLinked", "usedTotal", "percent", "overLimit", "blocked"}
    assert all(set(e) == allowed for e in body["employees"])


def test_department_employees_sum_to_department_and_show_leavers(pg):
    _org(pg)
    pg.client.put("/api/user-overrides/amaliyotchi", json={"blocked": True}).raise_for_status()

    it = portal(pg, "/departments/IT/employees", **PERIOD)["employees"]
    people = {e["login"]: e for e in it}
    assert people["ketgan"]["status"] == "inactive"
    assert people["amaliyotchi"]["blocked"] is True
    departments = {r["department"]: r for r in portal(pg, "/departments", **PERIOD)["departments"]}
    assert sum(e["used"] for e in it) == departments["IT"]["used"]


def test_department_with_slash_in_name_and_unknown_department(pg):
    sync(pg, person("ali", "AKT / Tizim"))
    send_jobs(pg, job(1, user="ali", pages=3))
    body = portal(pg, f"/departments/{quote('AKT / Tizim', safe='')}/employees", **PERIOD)
    assert [e["used"] for e in body["employees"]] == [3]

    r = pg.client.get("/api/portal/v1/departments/Yo'q bo'lim/employees", headers=HEADERS)
    assert r.status_code == 404


def test_new_endpoints_need_the_portal_key(pg):
    sync(pg, person("ali", XALQARO))
    for path in [
        "/api/portal/v1/periods",
        "/api/portal/v1/departments",
        f"/api/portal/v1/departments/{quote(XALQARO, safe='')}/employees",
        "/api/portal/v1/employees/ali/history",
    ]:
        assert pg.client.get(path).status_code == 401, path
        assert pg.client.get(path, headers={"X-Portal-Key": "notogri"}).status_code == 401, path

    r = pg.client.get(
        "/api/portal/v1/departments",
        params={"period_type": "quarter", "year": 2026, "period_no": 7},
        headers=HEADERS,
    )
    assert r.status_code == 422
