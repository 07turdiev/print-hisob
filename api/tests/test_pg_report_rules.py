r"""Hisobot raqamlari qoidalari: KPI, login kaliti, bekor qilingan ishlar (haqiqiy Postgres).

Qoidalarning to'liq ro'yxati: `docs/QOIDALAR.uz.md`.
"""

from datetime import datetime, timedelta, timezone

from test_pg_agent_contract import employee, job, send_jobs

NOW = datetime.now(timezone.utc)
PERIOD = {"period_type": "quarter", "year": NOW.year, "period_no": (NOW.month - 1) // 3 + 1}
CANCELLED = "Print job was canceled or deleted before completing"


def sync_employees(pg, *employees) -> None:
    pg.client.post("/api/ad-sync", json={"mode": "full", "employees": list(employees)}).raise_for_status()


def link(pg, login: str, owner: str) -> None:
    pg.client.put(f"/api/user-overrides/{login}", json={"chargeToLogin": owner}).raise_for_status()


def csv_rows(pg) -> list[list[str]]:
    r = pg.client.get("/api/stats/employees.csv", params=PERIOD)
    r.raise_for_status()
    return [line.split(",") for line in r.content.decode("utf-8-sig").splitlines()]


def stats(pg) -> dict[str, dict]:
    rows = pg.client.get("/api/stats/employees", params=PERIOD).json()
    return {r["login"].lower().rsplit("\\", 1)[-1]: r for r in rows}


def summary(pg) -> dict:
    return pg.client.get("/api/stats/summary", params=PERIOD).json()


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------


def test_kpi_includes_pages_of_linked_employees(pg):
    sync_employees(pg, employee("egasi"), employee("amaliyotchi"))
    send_jobs(pg, job(1, user="egasi", pages=10), job(2, user="amaliyotchi", pages=7))
    link(pg, "amaliyotchi", "egasi")

    rows = {r[1]: r[-1] for r in csv_rows(pg) if len(r) == 5 and r[0].isdigit()}
    assert rows == {"Egasi": "17", "Amaliyotchi": "7"}


def test_screen_total_matches_kpi(pg):
    sync_employees(pg, employee("egasi"), employee("amaliyotchi"))
    send_jobs(pg, job(1, user="egasi", pages=10), job(2, user="amaliyotchi", pages=7))
    link(pg, "amaliyotchi", "egasi")

    row = stats(pg)["egasi"]
    assert (row["used"], row["usedFromLinked"], row["usedTotal"]) == (10, 7, 17)


# ---------------------------------------------------------------------------
# Login kaliti
# ---------------------------------------------------------------------------


def test_login_spelling_does_not_split_a_person(pg):
    sync_employees(pg, employee("Ali.Valiyev"))
    send_jobs(pg, job(1, user="MADANIYAT\\ali.valiyev", pages=2), job(2, user="ali.valiyev", pages=3))

    row = stats(pg)["ali.valiyev"]
    assert (row["used"], row["department"], row["matchStatus"]) == (5, "IT", "active")


def test_department_views_see_every_spelling(pg):
    sync_employees(pg, employee("ali.valiyev"))
    send_jobs(pg, job(1, user="MADANIYAT\\Ali.Valiyev", pages=4))

    departments = pg.client.get("/api/stats/departments", params=PERIOD).json()
    assert [d["pages"] for d in departments if d["name"] == "IT"] == [4]
    filtered = pg.client.get("/api/stats/summary", params={**PERIOD, "department": "IT"}).json()
    assert filtered["totalPages"] == 4
    top = pg.client.get("/api/stats/top", params=PERIOD).json()
    assert [d["pages"] for d in top["departments"]] == [4]


def test_quota_saved_with_domain_applies_to_the_person(pg):
    sync_employees(pg, employee("ali"))
    send_jobs(pg, job(1, user="ali", pages=1))
    body = {
        "login": "MADANIYAT\\Ali",
        "periodType": PERIOD["period_type"],
        "year": PERIOD["year"],
        "periodNo": PERIOD["period_no"],
        "allocatedPages": 77,
    }
    saved = pg.client.put("/api/quotas", json=body)
    assert saved.status_code == 200
    assert saved.json()[0]["login"] == "ali"
    assert stats(pg)["ali"]["allocated"] == 77


def test_journal_user_filter_ignores_spelling(pg):
    send_jobs(pg, job(1, user="MADANIYAT\\Ali", pages=1), job(2, user="boshqa", pages=1))
    rows = pg.client.get("/api/print-jobs", params={"user": "ali"}).json()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Bekor qilingan ishlar va raqamlar
# ---------------------------------------------------------------------------


def test_cancelled_jobs_are_not_failures(pg):
    send_jobs(
        pg,
        job(1, pages=2),
        job(2, pages=0, success=False, reason=CANCELLED),
        job(3, pages=0, success=False, reason="Canceled by print quota: printing is blocked for this user"),
    )
    body = summary(pg)
    assert (body["totalJobs"], body["successRate"]) == (1, 1.0)


def test_real_failure_lowers_the_success_rate(pg):
    send_jobs(pg, job(1, pages=1), job(2, pages=0, success=False, reason="Printer offline"))
    body = summary(pg)
    assert (body["totalJobs"], body["successRate"]) == (2, 0.5)


def test_cancelled_jobs_stay_visible_in_journal_and_reasons(pg):
    send_jobs(pg, job(1, pages=0, success=False, reason=CANCELLED))
    assert len(pg.client.get("/api/print-jobs").json()) == 1
    reasons = pg.client.get("/api/stats/failures", params=PERIOD).json()
    assert reasons == [{"reason": CANCELLED, "count": 1}]


def test_printer_table_ignores_cancelled_jobs(pg):
    send_jobs(pg, job(1, pages=2), job(2, pages=0, success=False, reason=CANCELLED))
    row = pg.client.get("/api/stats/printers", params=PERIOD).json()[0]
    assert (row["jobs"], row["successRate"], row["failedJobs"]) == (1, 1.0, 0)


def test_active_printers_counts_devices_not_driver_names(pg):
    send_jobs(pg, job(1, printer="Canon Katta"), job(2, printer="Katta printer"), job(3, printer="Canon svetnoy"))
    assert summary(pg)["activePrinters"] == 1


def test_agent_tiles_match_the_table(pg):
    fresh = NOW.isoformat()
    old = (NOW - timedelta(days=3)).isoformat()
    for computer, working, moment in [("A", True, fresh), ("B", False, fresh), ("C", True, old), ("D", False, old)]:
        pg.client.post(
            "/api/agent-status", json={"computer": computer, "working": working, "timestamp": moment}
        ).raise_for_status()

    body = pg.client.get("/api/agents/summary").json()
    assert (body["total"], body["working"], body["notWorking"], body["stale"]) == (4, 1, 1, 2)


# ---------------------------------------------------------------------------
# Printer qoidalari va kirish
# ---------------------------------------------------------------------------


def test_replayed_old_job_does_not_move_the_current_ip(pg):
    send_jobs(pg, job(50, printerIp="192.168.20.200"))
    send_jobs(pg, job(1, printerIp="192.168.20.93"))
    assert pg.client.get("/api/printers").json()[0]["lastIp"] == "192.168.20.200"


def test_network_printer_does_not_join_a_usb_printer_with_the_same_name(pg):
    send_jobs(pg, job(1, printer="Canon Katta", printerMac="", printerIp=""))
    send_jobs(pg, job(2, printer="Canon Katta"))
    assert len(pg.client.get("/api/printers").json()) == 2


def test_group_policy_none_is_gone(pg):
    r = pg.client.post("/api/printer-groups", json={"name": "Taqiq", "policy": "none"})
    assert r.status_code == 422


def test_non_latin_login_is_rejected_cleanly(pg):
    r = pg.client.post("/api/auth/login", json={"username": "админ", "password": "пароль"})
    assert r.status_code == 401
