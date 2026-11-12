"""Ichki xizmatlar portali API'si (haqiqiy Postgres): `/api/portal/v1`.

Asosiy talab: portaldagi raqam dashboarddagi bilan bir xil bo'lishi va xodim
qaysi printerlardan chop eta olishini to'g'ri ko'rishi.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from test_pg_agent_contract import employee, job, send_jobs, sync
from test_pg_report_rules import CANCELLED, PERIOD, link, stats, sync_employees

NOW = datetime.now(timezone.utc)
KEY = "portal-sinov-kaliti"
OTHER_MAC, OTHER_IP = "40:F8:DF:00:00:01", "192.168.20.77"


@pytest.fixture(autouse=True)
def portal_key(monkeypatch):
    monkeypatch.setattr(settings, "portal_api_key", KEY)


def cabinet(pg, login: str, **params) -> dict:
    r = pg.client.get(
        f"/api/portal/v1/employees/{login}/printing", params=params, headers={"X-Portal-Key": KEY}
    )
    assert r.status_code == 200, r.text
    return r.json()


def device_ids(pg) -> dict[str, int]:
    return {d["lastIp"]: d["id"] for d in pg.client.get("/api/printers").json()}


# ---------------------------------------------------------------------------
# Norma
# ---------------------------------------------------------------------------


def test_quota_matches_the_dashboard(pg):
    sync_employees(pg, employee("egasi"), employee("amaliyotchi"))
    send_jobs(
        pg,
        job(1, user="MADANIYAT\\Egasi", pages=10),
        job(2, user="amaliyotchi", pages=7),
        job(3, user="egasi", pages=0, success=False, reason=CANCELLED),
        job(4, user="egasi", printer="Microsoft Print to PDF", printerMac="", printerIp="", pages=50),
    )
    link(pg, "amaliyotchi", "egasi")

    body = cabinet(pg, "Egasi")
    quota = body["quota"]
    row = stats(pg)["egasi"]
    assert (quota["used"], quota["usedFromLinked"], quota["usedTotal"]) == (
        row["used"],
        row["usedFromLinked"],
        row["usedTotal"],
    ) == (10, 7, 17)
    assert quota["allocated"] == row["allocated"] == settings.default_quota_quarter
    assert quota["remaining"] == settings.default_quota_quarter - 17
    assert quota["isDefault"] is True
    assert quota["linkedLogins"] == ["amaliyotchi"]
    assert body["employee"] == {
        "login": "egasi",
        "fullName": "Egasi",
        "department": "IT",
        "position": "Xodim",
        "status": "active",
    }
    assert body["period"]["periodType"] == "quarter"
    assert body["period"]["periodNo"] == PERIOD["period_no"]

    assert cabinet(pg, "amaliyotchi")["quota"]["chargedTo"] == "egasi"


def test_explicit_quota_and_percent(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(pg, job(1, user="ali", pages=30))
    pg.client.put(
        "/api/quotas",
        json={
            "login": "ali",
            "periodType": "quarter",
            "year": PERIOD["year"],
            "periodNo": PERIOD["period_no"],
            "allocatedPages": 40,
        },
    ).raise_for_status()

    quota = cabinet(pg, "ali")["quota"]
    assert (quota["allocated"], quota["remaining"], quota["percent"], quota["isDefault"]) == (
        40,
        10,
        75.0,
        False,
    )


def test_employee_without_prints_gets_an_empty_cabinet(pg):
    sync_employees(pg, employee("yangi"))

    body = cabinet(pg, "yangi")
    assert body["quota"]["used"] == 0
    assert body["quota"]["remaining"] == body["quota"]["allocated"]
    assert (body["printers"], body["daily"]) == ([], [])


def test_month_period_is_supported(pg):
    sync_employees(pg, employee("ali"))
    body = cabinet(pg, "ali", period_type="month")
    assert body["period"]["periodType"] == "month"
    assert body["quota"]["allocated"] == settings.default_quota_month


def test_unknown_login_is_404_but_history_only_login_is_found(pg):
    r = pg.client.get("/api/portal/v1/employees/hech.kim/printing", headers={"X-Portal-Key": KEY})
    assert r.status_code == 404

    send_jobs(pg, job(1, user="eski.xodim", pages=2))
    body = cabinet(pg, "eski.xodim")
    assert body["employee"]["status"] == "unknown"
    assert body["quota"]["used"] == 2


# ---------------------------------------------------------------------------
# Printer ruxsati
# ---------------------------------------------------------------------------


def test_restriction_off_means_all_printers(pg):
    sync_employees(pg, employee("ali"))
    access = cabinet(pg, "ali")["access"]
    assert (access["canPrint"], access["mode"], access["printers"]) == (True, "all", [])


def test_common_printers_and_used_printer_flags(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(pg, job(1, user="ali", pages=3), job(2, user="ali", printerMac=OTHER_MAC, printerIp=OTHER_IP))
    ids = device_ids(pg)
    pg.client.put(
        "/api/printer-access", json={"publicDeviceIds": [ids["192.168.20.93"]], "restrictDefault": True}
    ).raise_for_status()

    body = cabinet(pg, "ali")
    assert body["access"]["mode"] == "common"
    assert [(p["ip"], p["common"]) for p in body["access"]["printers"]] == [("192.168.20.93", True)]
    assert {p["ip"]: p["allowed"] for p in body["printers"]} == {
        "192.168.20.93": True,
        OTHER_IP: False,
    }
    # Kabinet agentga yuboriladigan ro'yxat bilan bir xil gapiradi.
    assert sync(pg, "ali").json()["allowedPrinters"] != ["*"]


def test_allowed_group_adds_its_printers(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(pg, job(1, user="ali"), job(2, user="ali", printerMac=OTHER_MAC, printerIp=OTHER_IP))
    ids = device_ids(pg)
    pg.client.put(
        "/api/printer-access", json={"publicDeviceIds": [ids["192.168.20.93"]], "restrictDefault": True}
    ).raise_for_status()
    group = pg.client.post("/api/printer-groups", json={"name": "Kotibiyat", "policy": "allowed"}).json()
    pg.client.put(
        f"/api/printer-groups/{group['id']}", json={"logins": ["ali"], "deviceIds": [ids[OTHER_IP]]}
    ).raise_for_status()

    body = cabinet(pg, "ali")
    access = body["access"]
    assert (access["mode"], access["groupName"]) == ("common_and_group", "Kotibiyat")
    assert [(p["ip"], p["common"]) for p in access["printers"]] == [
        ("192.168.20.93", True),
        (OTHER_IP, False),
    ]
    assert all(p["allowed"] for p in body["printers"])


def test_all_group_and_blocked_employee(pg):
    sync_employees(pg, employee("ali"), employee("vali"))
    send_jobs(pg, job(1, user="vali"))
    pg.client.put(
        "/api/printer-access",
        json={"publicDeviceIds": [device_ids(pg)["192.168.20.93"]], "restrictDefault": True},
    ).raise_for_status()
    group = pg.client.post("/api/printer-groups", json={"name": "Rahbariyat", "policy": "all"}).json()
    pg.client.put(f"/api/printer-groups/{group['id']}", json={"logins": ["ali"]}).raise_for_status()
    pg.client.put("/api/user-overrides/vali", json={"blocked": True}).raise_for_status()

    assert cabinet(pg, "ali")["access"]["mode"] == "all"
    blocked = cabinet(pg, "vali")
    assert (blocked["access"]["canPrint"], blocked["access"]["mode"]) == (False, "blocked")
    assert [p["allowed"] for p in blocked["printers"]] == [False]


# ---------------------------------------------------------------------------
# Kunlik sarf va ishlar ro'yxati
# ---------------------------------------------------------------------------


def test_daily_counts_only_own_counted_pages(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(
        pg,
        job(1, user="ali", pages=4),
        job(2, user="ali", pages=0, success=False, reason=CANCELLED),
        job(3, user="bob", pages=9),
    )
    daily = cabinet(pg, "ali")["daily"]
    assert sum(d["pages"] for d in daily) == 4
    assert sum(d["jobs"] for d in daily) == 1


def test_jobs_list_own_jobs_newest_first(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(
        pg,
        job(1, user="ali", pages=4),
        job(2, user="ali", printer="Microsoft Print to PDF", printerMac="", printerIp="", pages=3),
        job(3, user="bob", pages=9),
        job(4, user="MADANIYAT\\Ali", pages=0, success=False, reason=CANCELLED),
    )

    r = pg.client.get(
        "/api/portal/v1/employees/ali/jobs", params={"limit": 2}, headers={"X-Portal-Key": KEY}
    )
    assert r.status_code == 200
    assert r.headers["X-Total-Count"] == "3"
    rows = r.json()
    assert [(j["document"], j["counted"]) for j in rows] == [
        ("hujjat-4.docx", False),
        ("hujjat-2.docx", False),
    ]
    assert rows[0]["printer"] == "Canon Katta"
    assert rows[0]["printerIp"] == "192.168.20.93"

    since = (NOW - timedelta(minutes=118, seconds=30)).isoformat()
    later = pg.client.get(
        "/api/portal/v1/employees/ali/jobs", params={"since": since}, headers={"X-Portal-Key": KEY}
    )
    assert later.headers["X-Total-Count"] == "2"
