r"""Agent va AD skripti ishlatadigan to'rtta endpoint shartnomasi (haqiqiy Postgres).

Agent yopiq kod va 155 ta kompyuterda o'rnatilgan, shuning uchun so'rov va javob
shakli kelishuvsiz o'zgarmasligi kerak. Bu yerdagi JSON agent yuboradigan
ko'rinishda yozilgan. Test yiqilsa, kodni emas, avval shartnoma buzilgan-buzilmaganini
tekshiring.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings

NOW = datetime.now(timezone.utc)
MAC = "40:F8:DF:64:C6:97"
IP = "192.168.20.93"


def net_timestamp(moment: datetime) -> str:
    """.NET `DateTimeOffset.ToString("o")` ko'rinishi: 7 xonali kasr soniya."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f") + "7+00:00"


def job(i: int, user: str = "MADANIYAT\\ali", printer: str = "Canon Katta", pages: int = 1, **extra) -> dict:
    return {
        "user": user,
        "document": f"hujjat-{i}.docx",
        "printer": printer,
        "printerIp": IP,
        "printerMac": MAC,
        "pages": pages,
        "documentPages": pages,
        "duplex": False,
        "timestamp": net_timestamp(NOW - timedelta(minutes=120 - i)),
        "success": True,
        "reason": "",
        "jobId": str(i),
        **extra,
    }


def send_jobs(pg, *jobs, computer: str = "PC-1"):
    return pg.client.post("/api/print-jobs", json={"computer": computer, "jobs": list(jobs)})


def sync(pg, *users, computer: str = "PC-1"):
    return pg.client.post(
        "/api/print-quotas",
        json={
            "computer": computer,
            "periodKey": "",
            "timestamp": NOW.isoformat(),
            "users": [{"user": u, "pagesUsedHere": 0, "pagesUsed": 0, "limit": -1} for u in users],
        },
    )


def row_for(body: dict, login: str) -> dict:
    return next(u for u in body["users"] if u["user"].lower().rsplit("\\", 1)[-1] == login)


# ---------------------------------------------------------------------------
# POST /api/print-jobs
# ---------------------------------------------------------------------------


def test_print_jobs_contract(pg):
    r = send_jobs(pg, job(1, pages=2), job(2, printerMac="40-F8-DF-64-C6-97"))
    assert r.status_code == 201
    assert r.json() == {"computer": "PC-1", "received": 2, "inserted": 2, "duplicates": 0}

    rows = pg.sql("select user_name, pages, printer_mac, success from print_jobs order by id")
    assert [tuple(x) for x in rows] == [
        ("MADANIYAT\\ali", 2, MAC, True),
        ("MADANIYAT\\ali", 1, MAC, True),
    ]


def test_resending_a_batch_adds_nothing(pg):
    payload = [job(1), job(2)]
    assert send_jobs(pg, *payload).json()["inserted"] == 2

    again = send_jobs(pg, *payload)
    assert again.status_code == 201
    assert again.json() == {"computer": "PC-1", "received": 2, "inserted": 0, "duplicates": 2}
    assert pg.sql("select count(*) from print_jobs")[0][0] == 2


def test_old_agent_without_optional_fields(pg):
    minimal = {
        "user": "ali",
        "document": "eski.docx",
        "printer": "HP M404",
        "timestamp": "2026-07-10T14:32:10Z",
        "success": True,
    }
    assert send_jobs(pg, minimal).json()["inserted"] == 1
    row = pg.sql("select pages, printer_ip, printer_mac, job_id, duplex from print_jobs")[0]
    assert tuple(row) == (0, None, None, None, False)


def test_empty_strings_are_stored_as_null(pg):
    send_jobs(pg, job(1, printerIp="", printerMac="", jobId=""))
    assert tuple(pg.sql("select printer_ip, printer_mac, job_id from print_jobs")[0]) == (None, None, None)


def test_one_invalid_event_rejects_the_whole_batch(pg):
    r = send_jobs(pg, job(1), job(2, pages=-1))
    assert r.status_code == 422
    assert pg.sql("select count(*) from print_jobs")[0][0] == 0


# ---------------------------------------------------------------------------
# POST /api/agent-status
# ---------------------------------------------------------------------------


def status_payload(**extra) -> dict:
    return {
        "computer": "PC-1",
        "username": "Ali Valiyev",
        "version": "1.6.1.0",
        "working": True,
        "detail": "",
        "bootTimeUtc": "2026-11-09T05:12:44+00:00",
        "uptimeSeconds": 3600,
        "agentUptimeSeconds": 60,
        "timestamp": NOW.isoformat(),
        **extra,
    }


def test_agent_status_keeps_one_row_per_computer(pg):
    r = pg.client.post("/api/agent-status", json=status_payload())
    assert r.status_code == 200
    assert r.json() == {"computer": "PC-1", "status": "ok"}

    pg.client.post("/api/agent-status", json=status_payload(version="1.7.0.0", working=False))
    rows = pg.sql("select version, working from agent_status")
    assert [tuple(x) for x in rows] == [("1.7.0.0", False)]


def test_agent_status_from_old_agent(pg):
    r = pg.client.post(
        "/api/agent-status",
        json={"computer": "PC-2", "working": True, "timestamp": "2026-07-23T09:38:47Z"},
    )
    assert r.status_code == 200
    assert tuple(pg.sql("select version, boot_time_utc from agent_status")[0]) == (None, None)


# ---------------------------------------------------------------------------
# POST /api/print-quotas
# ---------------------------------------------------------------------------


def test_print_quotas_response_shape(pg):
    send_jobs(pg, job(1, pages=3))
    r = sync(pg, "MADANIYAT\\ali")
    assert r.status_code == 200

    body = r.json()
    assert set(body) == {"periodKey", "defaultLimit", "allowedPrinters", "users"}
    assert body["periodKey"] == f"{NOW.year}-Q{(NOW.month - 1) // 3 + 1}"
    assert body["defaultLimit"] == -1
    assert body["allowedPrinters"] == ["*"]
    assert body["users"] == [
        {"user": "MADANIYAT\\ali", "limit": -1, "used": 3, "allowedPrinters": ["*"]}
    ]


def test_used_does_not_count_virtual_printers(pg):
    send_jobs(pg, job(1, pages=3), job(2, printer="Microsoft Print to PDF", pages=50, printerIp="", printerMac=""))
    assert row_for(sync(pg, "ali").json(), "ali")["used"] == 3


def test_block_and_explicit_unblock_reach_the_agent(pg):
    pg.client.put("/api/user-overrides/ali", json={"blocked": True}).raise_for_status()
    blocked = row_for(sync(pg, "ali").json(), "ali")
    assert (blocked["limit"], blocked["allowedPrinters"]) == (0, [])

    pg.client.put("/api/user-overrides/ali", json={"blocked": False}).raise_for_status()
    # Agent javobni keshlaydi: blokdan chiqqan xodim so'ralmasa ham aniq -1 olishi kerak.
    opened = row_for(sync(pg, "boshqa").json(), "ali")
    assert (opened["limit"], opened["allowedPrinters"]) == (-1, None)


def test_two_spellings_of_one_login_in_one_request(pg):
    """Bir kompyuterda bir odam ikki xil yozilishi mumkin: bu 500 bermasligi kerak."""
    r = sync(pg, "MADANIYAT\\ali", "ali")
    assert r.status_code == 200
    assert pg.sql("select count(*) from agent_quota_state")[0][0] == 1


def _public_printer(pg) -> int:
    send_jobs(pg, job(1))
    return pg.client.get("/api/printers").json()[0]["id"]


def test_restriction_sends_mac_and_current_ip(pg):
    device_id = _public_printer(pg)
    pg.client.put("/api/printer-access", json={"publicDeviceIds": [device_id], "restrictDefault": True}).raise_for_status()

    body = sync(pg, "ali").json()
    assert sorted(body["allowedPrinters"]) == sorted([MAC, IP])
    assert sorted(row_for(body, "ali")["allowedPrinters"]) == sorted([MAC, IP])


def test_restriction_off_keeps_everyone_open(pg):
    device_id = _public_printer(pg)
    pg.client.put("/api/printer-access", json={"publicDeviceIds": [device_id]}).raise_for_status()
    assert sync(pg, "ali").json()["allowedPrinters"] == ["*"]


def test_group_login_gets_its_own_list_while_restriction_is_off(pg):
    """Agent dasturchisi sinovi shunga tayanadi: boshqa xodimlarga ta'sir qilmaydi."""
    device_id = _public_printer(pg)
    pg.client.put("/api/printer-access", json={"publicDeviceIds": [device_id]}).raise_for_status()
    group = pg.client.post("/api/printer-groups", json={"name": "Sinov", "policy": "allowed"}).json()
    pg.client.put(f"/api/printer-groups/{group['id']}", json={"logins": ["sinov"]}).raise_for_status()

    body = sync(pg, "sinov", "ali").json()
    assert sorted(row_for(body, "sinov")["allowedPrinters"]) == sorted([MAC, IP])
    assert row_for(body, "ali")["allowedPrinters"] == ["*"]
    assert body["allowedPrinters"] == ["*"]


# ---------------------------------------------------------------------------
# POST /api/ad-sync
# ---------------------------------------------------------------------------


def employee(login: str) -> dict:
    return {"login": login, "fullName": login.title(), "department": "IT", "position": "Xodim", "active": True}


def test_full_ad_sync_deactivates_missing_employees(pg):
    first = pg.client.post("/api/ad-sync", json={"mode": "full", "employees": [employee("ali"), employee("bob")]})
    assert first.status_code == 200
    assert first.json() == {"mode": "full", "received": 2, "upserted": 2, "deactivated": 0}

    second = pg.client.post("/api/ad-sync", json={"mode": "full", "employees": [employee("ali")]})
    assert second.json() == {"mode": "full", "received": 1, "upserted": 1, "deactivated": 1}
    assert pg.sql("select login from employees where is_active")[0][0] == "ali"


# ---------------------------------------------------------------------------
# X-Api-Key
# ---------------------------------------------------------------------------

AGENT_CALLS = [
    ("/api/print-jobs", {"computer": "PC-1", "jobs": []}),
    ("/api/agent-status", {"computer": "PC-1", "working": True, "timestamp": "2026-11-09T00:00:00Z"}),
    ("/api/print-quotas", {"computer": "PC-1", "timestamp": "2026-11-09T00:00:00Z", "users": []}),
    ("/api/ad-sync", {"mode": "delta", "employees": []}),
]


@pytest.mark.parametrize(("path", "payload"), AGENT_CALLS)
def test_machine_endpoints_require_the_key(pg, monkeypatch, path, payload):
    monkeypatch.setattr(settings, "api_key", "sinov-kaliti")
    pg.client.headers.pop("Authorization")

    assert pg.client.post(path, json=payload).status_code == 401
    assert pg.client.post(path, json=payload, headers={"X-Api-Key": "xato"}).status_code == 401
    # Agent sarlavhani `X-Api-Key`, AD skripti `X-API-Key` deb yuboradi.
    for header in ("X-Api-Key", "X-API-Key"):
        assert pg.client.post(path, json=payload, headers={header: "sinov-kaliti"}).status_code in (200, 201)
