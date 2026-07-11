"""`GET /api/stats/employees.csv` uchun baza talab qilmaydigan testlar.

`_employee_stats_rows` (SQL agregatsiyasi) `conftest.FakeSession` bilan har doim
bo'sh natija qaytaradi, shuning uchun bu yerda uni to'g'ridan-to'g'ri
mock qilib, faqat CSV formatlash (BOM, sarlavha, bo'lim guruhlash,
"Noma'lum foydalanuvchilar" bo'limi) tekshiriladi.
"""

from unittest.mock import AsyncMock

import app.main as main_module
from app.schemas import EmployeeStatOut

PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}

_ROWS = [
    EmployeeStatOut(
        login="nsarvar",
        full_name="Nosirov Sarvar Nodirovich",
        department="Ichki audit bo'limi",
        position="Bo'lim boshlig'i",
        used=310,
        allocated=334,
        remaining=24,
        over_limit=False,
        match_status="active",
    ),
    EmployeeStatOut(
        login="ex-employee",
        full_name="Aliyev Vali",
        department="Ichki audit bo'limi",
        position="Mutaxassis",
        used=50,
        allocated=0,
        remaining=-50,
        over_limit=True,
        match_status="inactive",
    ),
    EmployeeStatOut(
        login="ghost1",
        full_name=None,
        department=None,
        position=None,
        used=42,
        allocated=0,
        remaining=-42,
        over_limit=True,
        match_status="unmatched",
    ),
]


def test_employees_csv_returns_csv_content_type(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=[]))
    r = client.get("/api/stats/employees.csv", params=PERIOD)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


def test_employees_csv_starts_with_bom_and_header(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=_ROWS))
    r = client.get("/api/stats/employees.csv", params=PERIOD)
    body = r.content.decode("utf-8")
    assert body.startswith("﻿")
    lines = body[1:].splitlines()
    assert lines[0] == "T/r,F.I.SH.,Lavozimi,3-chorak,Qog'oz sarfi 3-chorak"


def test_employees_csv_groups_by_department(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=_ROWS))
    r = client.get("/api/stats/employees.csv", params=PERIOD)
    lines = r.content.decode("utf-8")[1:].splitlines()

    # Xodimlar bo'lim ichida F.I.SH. bo'yicha alifbo tartibida: "Aliyev" < "Nosirov".
    assert lines[1] == "Ichki audit bo'limi,,,,"
    assert lines[2] == "1,Aliyev Vali,Mutaxassis,0,50"
    # Ishdan bo'shagan (inactive) xodim ham o'z bo'limida qoladi.
    assert lines[3] == "2,Nosirov Sarvar Nodirovich,Bo'lim boshlig'i,334,310"


def test_employees_csv_unmatched_section(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=_ROWS))
    r = client.get("/api/stats/employees.csv", params=PERIOD)
    body = r.content.decode("utf-8")
    assert "Noma'lum foydalanuvchilar" in body
    assert "ghost1" in body


def test_employees_csv_filename_header(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=[]))
    r = client.get("/api/stats/employees.csv", params=PERIOD)
    disposition = r.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "2026" in disposition
    assert "filename*=UTF-8''" in disposition


def test_employees_csv_month_period_label(client, monkeypatch):
    monkeypatch.setattr(main_module, "_employee_stats_rows", AsyncMock(return_value=[]))
    r = client.get(
        "/api/stats/employees.csv",
        params={"period_type": "month", "year": 2026, "period_no": 7},
    )
    body = r.content.decode("utf-8")
    assert "Iyul" in body


def test_employees_csv_requires_bearer_token():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/stats/employees.csv", params=PERIOD)
    assert r.status_code == 401
